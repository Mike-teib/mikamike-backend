"""
importers.py — Import STRICT des artefacts du chantier local (Phases 20 et 23).

Arborescence attendue :
  <dossier>/IMPORT_MANIFEST.json
      {"version": 1, "fichiers": [{"chemin": "...", "sha256": "...", "type": "..."}]}
  <dossier>/<fichiers listés>

Types :
  referentiel              JSON  : objet Referentiel canonique complet
  registre_notions         JSONL : une Notion par ligne
  mapping_notion_chapitre  JSONL : {"notion_id", "chapitre_id"} (appliqué au registre)
  index_contenus           JSONL : {"kind": "exercice"|"quiz", "data": {...}}
  opaque                   tout autre artefact (rapports d'audit, résultats C02 /
                           C02-6.1, Extraction V3, M01 Maths Cycle 3…) : formats
                           NON documentés dans ce dépôt ⇒ ni interprétés ni devinés ;
                           empreinte vérifiée et consignée, statut OPAQUE_A_MAPPER.

Garanties :
  - manifest obligatoire ; empreinte SHA-256 de chaque fichier vérifiée ;
    fichier non listé, manquant ou chemin sortant du dossier ⇒ rejet ;
  - lecture JSONL en flux (ligne à ligne) : pas de chargement complet en mémoire ;
  - tout-ou-rien PAR FICHIER, état FAILED explicite avec ligne et raison ;
  - checkpoint : un fichier DONE (même empreinte) n'est jamais retraité ;
    une reprise après interruption repart du premier fichier non terminé ;
  - dépistage de données personnelles (clés nominatives, e-mails, téléphones) ⇒ FAILED ;
  - validation structurelle finale : statut VALIDATED seulement si 0 anomalie.
Aucune écriture hors du fichier de checkpoint fourni par l'appelant.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

from pydantic import ValidationError

from app.curriculum.exercices import Exercice
from app.curriculum.model import Notion, Referentiel
from app.curriculum.quiz import QuestionQuiz
from app.curriculum.structure import Anomalie, valider_referentiel

NOM_MANIFEST = "IMPORT_MANIFEST.json"
TYPES = ("referentiel", "registre_notions", "mapping_notion_chapitre", "index_contenus", "opaque")
MAX_LIGNE = 1_000_000  # octets par ligne JSONL

_CLES_PERSONNELLES = {"nom", "prenom", "email", "mail", "telephone", "tel", "adresse", "date_naissance",
                      "eleve_nom", "nom_eleve", "prenom_eleve", "ip", "photo"}
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_TEL = re.compile(r"(?<![\w.])(?:\+33\s?|0)[67](?:[\s.\-]?\d{2}){4}(?![\w.])")


class ErreurImport(ValueError):
    pass


def sha256_fichier(chemin: Path) -> str:
    h = hashlib.sha256()
    with chemin.open("rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def _cles_recursives(obj: Any) -> Iterator[str]:
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield str(k).lower()
            yield from _cles_recursives(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _cles_recursives(v)


def _depister_pii(obj: Any, texte: str) -> Optional[str]:
    cles = set(_cles_recursives(obj)) & _CLES_PERSONNELLES
    if cles:
        return "cle_personnelle:" + ",".join(sorted(cles))
    if _EMAIL.search(texte):
        return "email_detecte"
    if _TEL.search(texte):
        return "telephone_detecte"
    return None


def _lignes_jsonl(chemin: Path) -> Iterator[Tuple[int, Any]]:
    with chemin.open("r", encoding="utf-8") as f:
        for num, ligne in enumerate(f, start=1):
            if len(ligne) > MAX_LIGNE:
                raise ErreurImport(f"ligne_{num}_trop_longue")
            if not ligne.strip():
                continue
            try:
                obj = json.loads(ligne)
            except json.JSONDecodeError as exc:
                raise ErreurImport(f"ligne_{num}_json_invalide") from exc
            pii = _depister_pii(obj, ligne)
            if pii:
                raise ErreurImport(f"ligne_{num}_{pii}")
            yield num, obj


@dataclass
class ResultatImport:
    statut: str = "PENDING"  # VALIDATED | REJECTED | FAILED
    fichiers: Dict[str, Dict[str, str]] = field(default_factory=dict)
    referentiel: Optional[Referentiel] = None
    exercices: List[Exercice] = field(default_factory=list)
    quiz: List[QuestionQuiz] = field(default_factory=list)
    opaques: List[Dict[str, str]] = field(default_factory=list)
    anomalies: List[Anomalie] = field(default_factory=list)


def _charger_checkpoint(chemin: Optional[Path]) -> Dict[str, Dict[str, str]]:
    if chemin and chemin.exists():
        return json.loads(chemin.read_text(encoding="utf-8"))
    return {}


def _ecrire_checkpoint(chemin: Optional[Path], etat: Dict[str, Dict[str, str]]) -> None:
    if chemin is None:
        return
    chemin.parent.mkdir(parents=True, exist_ok=True)
    tmp = chemin.with_suffix(".tmp")
    tmp.write_text(json.dumps(etat, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    tmp.replace(chemin)  # écriture atomique


def lire_manifest(dossier: Path) -> List[Dict[str, str]]:
    m = dossier / NOM_MANIFEST
    if not m.is_file():
        raise ErreurImport("manifest_absent")
    data = json.loads(m.read_text(encoding="utf-8"))
    if data.get("version") != 1 or not isinstance(data.get("fichiers"), list):
        raise ErreurImport("manifest_version_ou_format_invalide")
    racine = dossier.resolve()
    vus = set()
    for f in data["fichiers"]:
        if set(f) != {"chemin", "sha256", "type"}:
            raise ErreurImport("entree_manifest_invalide")
        if f["type"] not in TYPES:
            raise ErreurImport(f"type_inconnu:{f['type']}")
        if not re.fullmatch(r"[0-9a-f]{64}", f["sha256"]):
            raise ErreurImport("sha256_manifest_invalide")
        cible = (dossier / f["chemin"]).resolve()
        if racine not in cible.parents:
            raise ErreurImport(f"chemin_hors_dossier:{f['chemin']}")
        if f["chemin"] in vus:
            raise ErreurImport(f"fichier_liste_deux_fois:{f['chemin']}")
        vus.add(f["chemin"])
    presents = {str(p.relative_to(dossier)) for p in dossier.rglob("*") if p.is_file()} - {NOM_MANIFEST}
    non_listes = sorted(presents - vus)
    if non_listes:
        raise ErreurImport("fichiers_non_listes:" + ",".join(non_listes))
    return data["fichiers"]


def importer(dossier: Path, *, checkpoint: Optional[Path] = None) -> ResultatImport:
    res = ResultatImport()
    try:
        entrees = lire_manifest(dossier)
    except (ErreurImport, json.JSONDecodeError) as exc:
        res.statut = "FAILED"
        res.fichiers[NOM_MANIFEST] = {"etat": "FAILED", "raison": str(exc)}
        return res

    etat = _charger_checkpoint(checkpoint)
    ref_base: Optional[Referentiel] = None
    notions: Dict[str, Notion] = {}
    mappings: List[Tuple[str, str]] = []

    for e in entrees:
        chemin, attendu, type_ = dossier / e["chemin"], e["sha256"], e["type"]
        cle = e["chemin"]
        try:
            if not chemin.is_file():
                raise ErreurImport("fichier_manquant")
            reel = sha256_fichier(chemin)
            if reel != attendu:
                raise ErreurImport("empreinte_differente")
            deja = etat.get(cle, {})
            reprise = deja.get("etat") == "DONE" and deja.get("sha256") == reel

            if type_ == "referentiel":
                texte = chemin.read_text(encoding="utf-8")
                obj = json.loads(texte)
                pii = _depister_pii(obj, texte)
                if pii:
                    raise ErreurImport(pii)
                ref_base = Referentiel.model_validate(obj)
            elif type_ == "registre_notions":
                lot = {}
                for num, obj in _lignes_jsonl(chemin):
                    n = Notion.model_validate(obj)
                    if n.id in lot or n.id in notions:
                        raise ErreurImport(f"ligne_{num}_notion_dupliquee")
                    lot[n.id] = n
                notions.update(lot)
            elif type_ == "mapping_notion_chapitre":
                lot_m = []
                for num, obj in _lignes_jsonl(chemin):
                    if not isinstance(obj, dict) or set(obj) != {"notion_id", "chapitre_id"}:
                        raise ErreurImport(f"ligne_{num}_mapping_invalide")
                    lot_m.append((obj["notion_id"], obj["chapitre_id"]))
                mappings.extend(lot_m)
            elif type_ == "index_contenus":
                ex_lot, q_lot = [], []
                for num, obj in _lignes_jsonl(chemin):
                    kind = obj.get("kind") if isinstance(obj, dict) else None
                    if kind == "exercice":
                        ex_lot.append(Exercice.model_validate(obj.get("data")))
                    elif kind == "quiz":
                        q_lot.append(QuestionQuiz.model_validate(obj.get("data")))
                    else:
                        raise ErreurImport(f"ligne_{num}_kind_inconnu")
                res.exercices.extend(ex_lot)
                res.quiz.extend(q_lot)
            else:  # opaque
                res.opaques.append({"chemin": cle, "sha256": reel, "statut": "OPAQUE_A_MAPPER"})

            res.fichiers[cle] = {"etat": "DONE", "sha256": reel, "reprise": str(reprise).lower()}
            etat[cle] = {"etat": "DONE", "sha256": reel}
        except (ErreurImport, ValidationError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raison = str(exc).splitlines()[0] if not isinstance(exc, ValidationError) else \
                f"schema_invalide:{exc.error_count()}_erreur(s)"
            res.fichiers[cle] = {"etat": "FAILED", "raison": raison}
            etat[cle] = {"etat": "FAILED", "raison": raison}
        _ecrire_checkpoint(checkpoint, etat)

    if any(f["etat"] == "FAILED" for f in res.fichiers.values()):
        res.statut = "FAILED"
        return res

    # Assemblage + application stricte des mappings.
    base = ref_base or Referentiel()
    toutes = {n.id: n for n in base.notions}
    for nid, n in notions.items():
        if nid in toutes:
            res.anomalies.append(Anomalie("IMPORT_NOTION_EN_CONFLIT", nid))
        toutes[nid] = n
    chap_ids = {c.id for c in base.chapitres}
    for nid, cid in mappings:
        if nid not in toutes:
            res.anomalies.append(Anomalie("MAPPING_NOTION_INCONNUE", nid, cid))
        elif cid not in chap_ids:
            res.anomalies.append(Anomalie("MAPPING_CHAPITRE_INCONNU", nid, cid))
        else:
            toutes[nid] = toutes[nid].model_copy(update={"chapitre_id": cid})

    ref = base.model_copy(update={"notions": tuple(toutes[k] for k in sorted(toutes))})
    res.referentiel = ref
    res.anomalies.extend(valider_referentiel(ref))
    res.anomalies.sort()
    res.statut = "VALIDATED" if not res.anomalies else "REJECTED"
    return res


def ecrire_manifest(dossier: Path, types: Dict[str, str]) -> Path:
    """Utilitaire (côté producteur) : génère le manifest à partir des fichiers présents."""
    fichiers = [
        {"chemin": chemin, "sha256": sha256_fichier(dossier / chemin), "type": type_}
        for chemin, type_ in sorted(types.items())
    ]
    m = dossier / NOM_MANIFEST
    m.write_text(json.dumps({"version": 1, "fichiers": fichiers}, indent=2, ensure_ascii=False), encoding="utf-8")
    return m
