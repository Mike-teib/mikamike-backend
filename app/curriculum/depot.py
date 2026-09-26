"""
depot.py — Publication, activation atomique et ROLLBACK des lots de contenu importés.

Arborescence (répertoire fourni par l'exploitant, jamais écrit ailleurs) :
  <racine>/lots/<lot_id>-<sha8>/      copie IMMUABLE d'un lot VALIDATED (manifest v2 inclus)
  <racine>/ACTIF.json                 {"lot", "sha256_manifest", "precedent"} (écriture atomique)
  <racine>/HISTORIQUE.jsonl           journal append-only des activations / rollbacks

Garanties :
  - on ne publie qu'un lot dont l'import (manifest ÉPINGLÉ) est VALIDATED ;
  - un lot publié n'est jamais écrasé (même dossier ⇒ refus) ;
  - activation = remplacement atomique d'ACTIF.json ; en cas d'échec, l'ancien lot reste actif ;
  - `rollback` réactive le lot précédent APRÈS l'avoir ré-importé et revalidé ;
  - `charger_actif` ré-importe le lot actif avec son empreinte épinglée : un lot altéré sur
    disque après publication est REFUSÉ (fail-closed), jamais servi.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from app.curriculum.importers import ResultatImport, importer, lire_manifest_complet


class DepotInvalide(RuntimeError):
    pass


class DepotContenu:
    def __init__(self, racine: Path, *, autoriser_fictif: bool = False):
        self.racine = Path(racine)
        self.autoriser_fictif = autoriser_fictif

    # ------------------------------------------------------------------ interne
    @property
    def _actif(self) -> Path:
        return self.racine / "ACTIF.json"

    def _ecrire_actif(self, etat: Dict[str, Any]) -> None:
        self.racine.mkdir(parents=True, exist_ok=True)
        tmp = self._actif.with_suffix(".tmp")
        tmp.write_text(json.dumps(etat, sort_keys=True, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self._actif)  # atomique (même système de fichiers)

    def _journal(self, evenement: Dict[str, Any]) -> None:
        with (self.racine / "HISTORIQUE.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(evenement, sort_keys=True, ensure_ascii=False) + "\n")

    def _importer(self, dossier: Path, sha: str) -> ResultatImport:
        return importer(dossier, sha256_manifest=sha, autoriser_fictif=self.autoriser_fictif)

    # ------------------------------------------------------------------ API
    def actif(self) -> Optional[Dict[str, Any]]:
        if not self._actif.exists():
            return None
        try:
            etat = json.loads(self._actif.read_text(encoding="utf-8"))
        except (ValueError, RecursionError) as exc:
            raise DepotInvalide("ACTIF.json illisible") from exc
        if not isinstance(etat, dict) or not {"lot", "sha256_manifest", "precedent"} <= set(etat):
            raise DepotInvalide("ACTIF.json invalide")
        return etat

    def publier(self, dossier_lot: Path, sha256_manifest: str) -> ResultatImport:
        """Importe (manifest épinglé), copie le lot validé puis l'ACTIVE. Rien n'est activé sinon."""
        res = self._importer(Path(dossier_lot), sha256_manifest)
        if res.statut != "VALIDATED":
            return res
        lot = f"{res.manifest['lot_id']}-{sha256_manifest[:8]}"
        cible = self.racine / "lots" / lot
        precedent = self.actif()
        if cible.exists():
            # Revue session 3 (S3-16) : une publication coupée entre la copie et l'activation ne
            # pouvait plus JAMAIS aboutir (« lot_deja_publie »). Lot déjà ACTIF ⇒ refus (contrat
            # inchangé, rien ne bouge) ; copie présente mais NON active ⇒ reprise : copie
            # revalidée (jamais écrasée) puis activation.
            if precedent and precedent["lot"] == lot:
                raise DepotInvalide(f"lot_deja_publie:{lot}")
            if self._importer(cible, sha256_manifest).statut != "VALIDATED":
                raise DepotInvalide(f"copie_existante_invalide:{lot}")
            self._activer(lot, sha256_manifest, precedent, action="reprendre")
            return res
        cible.parent.mkdir(parents=True, exist_ok=True)
        tmp = cible.with_name(cible.name + ".tmp")
        if tmp.exists():
            shutil.rmtree(tmp)
        shutil.copytree(dossier_lot, tmp)
        # Revalidation de la COPIE (disque de destination) avant de la rendre visible.
        if self._importer(tmp, sha256_manifest).statut != "VALIDATED":
            shutil.rmtree(tmp)
            raise DepotInvalide("copie_du_lot_invalide")
        os.replace(tmp, cible)
        self._activer(lot, sha256_manifest, precedent, action="activer")
        return res

    def _activer(self, lot: str, sha: str, precedent: Optional[Dict[str, Any]], *, action: str) -> None:
        self._ecrire_actif({"lot": lot, "sha256_manifest": sha, "precedent": _borner(precedent)})
        self._journal({"action": action, "lot": lot})

    def charger_actif(self) -> Optional[ResultatImport]:
        etat = self.actif()
        if etat is None:
            return None
        res = self._importer(self.racine / "lots" / etat["lot"], etat["sha256_manifest"])
        if res.statut != "VALIDATED":
            raise DepotInvalide(f"lot_actif_invalide:{etat['lot']}")
        return res

    def rollback(self) -> Optional[str]:
        """Réactive le lot précédent (revalidé). Renvoie son nom, ou None s'il n'y en a pas."""
        etat = self.actif()
        if etat is None or not etat.get("precedent"):
            raise DepotInvalide("aucun_lot_precedent")
        prec = etat["precedent"]
        res = self._importer(self.racine / "lots" / prec["lot"], prec["sha256_manifest"])
        if res.statut != "VALIDATED":
            raise DepotInvalide(f"lot_precedent_invalide:{prec['lot']}")
        self._ecrire_actif(prec)
        self._journal({"action": "rollback", "depuis": etat["lot"], "vers": prec["lot"]})
        return prec["lot"]


PROFONDEUR_HISTORIQUE = 20


def _borner(etat: Optional[Dict[str, Any]], profondeur: int = PROFONDEUR_HISTORIQUE) -> Optional[Dict[str, Any]]:
    """Chaîne `precedent` bornée (S3-16) : elle s'imbriquait à chaque publication, sans limite
    (ACTIF.json croissant, puis illisible au-delà de la limite de récursion de json)."""
    if not etat or profondeur <= 0:
        return None
    return {"lot": etat["lot"], "sha256_manifest": etat["sha256_manifest"],
            "precedent": _borner(etat.get("precedent"), profondeur - 1)}


def lot_id(dossier: Path, sha256_manifest: str) -> str:
    return lire_manifest_complet(dossier, sha256_manifest=sha256_manifest)["lot_id"]


def catalogue_depuis_import(res: ResultatImport, *, autoriser_fictif: bool = False):
    """Construit le catalogue du tuteur à partir d'un import VALIDATED (fail-closed sinon)."""
    from app.api.v1.tutorat.contenu import CatalogueTutorat

    if res.statut != "VALIDATED" or res.referentiel is None:
        raise DepotInvalide("import_non_valide")
    return CatalogueTutorat(res.referentiel, res.exercices, res.plans, autoriser_fictif=autoriser_fictif)
