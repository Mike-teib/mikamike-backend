"""
publication.py — Garde de publication des contenus (lot 30, session 4).

Trois états, jamais confondus :
  BLOQUE                 au moins une condition manque (raisons listées) ;
  READY_FOR_PUBLICATION  toutes les conditions sont démontrées — rien n'est encore visible ;
  PUBLISHED              une personne (opérateur nommé) a publié ce contenu PRÊT ; la publication
                         est liée à l'EMPREINTE du contenu : un contenu modifié redevient seulement
                         READY (il faut le republier).

Conditions (toutes obligatoires) :
  LOT_VALIDE          le lot actif est VALIDATED (intégrité croisée démontrée) ;
  SOURCE_PROUVEE      source non fictive (hors mode test) dont le document est dans le lot ;
  NOTION_PROUVEE      notion PROVEN, générable (aucune anomalie ne la touche) ;
  TEXTE_SAIN          texte de la notion ET énoncé recalculés utilisables ;
  CHAPITRE_PROUVE     rattachée à un chapitre existant, non ambigu, du même programme ;
  STRUCTURE_VALIDE    aucune anomalie de structure sur la notion, son chapitre, son programme ;
  VALIDATION_OK       réponse vérifiable (exercice) / question valide (quiz) ;
  PLAN_VALIDE         exercice : plan de guidage présent et valide (servi par le tuteur).

Journal append-only : `<depot>/PUBLICATIONS.jsonl` (publier / retirer, opérateur, date, empreinte).
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
from enum import Enum
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional

from app.curriculum.importers import ResultatImport
from app.curriculum.model import StatutPreuve, StatutTexte
from app.curriculum.provenance import evaluer_preuve
from app.curriculum.text_quality import analyser_texte
from app.curriculum.verifiers.base import Verdict
from app.curriculum.verifiers.dispatch import verifier

STATUTS_TEXTE_SAINS = {StatutTexte.TEXT_EXACT, StatutTexte.TEXT_RECOVERED}
_OPERATEUR = re.compile(r"^[a-z0-9][a-z0-9._\-]{1,63}$")


class EtatPublication(str, Enum):
    BLOQUE = "BLOQUE"
    READY_FOR_PUBLICATION = "READY_FOR_PUBLICATION"
    PUBLISHED = "PUBLISHED"


class Evaluation(NamedTuple):
    contenu_id: str
    etat: EtatPublication
    raisons: tuple
    empreinte: str


class PublicationRefusee(ValueError):
    pass


def empreinte_contenu(contenu) -> str:
    brut = json.dumps(contenu.model_dump(mode="json"), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(brut.encode("utf-8")).hexdigest()


def _raisons(res: ResultatImport, contenu, *, est_exercice: bool, autoriser_fictif: bool) -> List[str]:
    r: List[str] = []
    if res.statut != "VALIDATED" or res.referentiel is None or res.integrite is None:
        return ["LOT_NON_VALIDE"]
    idx = res.referentiel.index()
    n = idx.notions.get(contenu.notion_id)
    if n is None:
        return ["NOTION_INCONNUE"]
    prog = idx.programmes.get(n.programme_id)
    source = idx.sources.get(prog.source_id) if prog else None
    if source is None or (source.fictive and not autoriser_fictif) or (
            not source.fictive and source.sha256_document not in set(res.documents.values())):
        r.append("SOURCE_NON_PROUVEE")
    statut = evaluer_preuve(n, idx.sources.get(n.preuve.source_id) if n.preuve else None,
                            autoriser_fictif=autoriser_fictif).statut
    if statut != StatutPreuve.PROVEN or n.id not in res.integrite.generables:
        r.append("NOTION_NON_PROUVEE")
    if analyser_texte(n.texte).statut not in STATUTS_TEXTE_SAINS or \
            analyser_texte(contenu.enonce).statut not in STATUTS_TEXTE_SAINS:
        r.append("TEXTE_NON_SAIN")
    chap = idx.chapitres.get(n.chapitre_id) if n.chapitre_id else None
    if chap is None or chap.ambigu or chap.programme_id != n.programme_id:
        r.append("CHAPITRE_NON_PROUVE")
    elif res.rattachements.get(n.id) != "PROUVE":  # lot 8 : rattachement prouvé par la structure
        r.append("CHAPITRE_NON_PROUVE")
    touches = {a.objet_id for a in res.anomalies}
    if {n.id, n.chapitre_id, n.programme_id, contenu.id} & touches:
        r.append("STRUCTURE_INVALIDE")
    if est_exercice:
        v = verifier(contenu.type_verification, contenu.reponse_attendue, contenu.reponse_attendue,
                     contenu.parametres_verification)
        if v.verdict != Verdict.VALID:
            r.append("VALIDATION_ECHOUEE")
        if contenu.id not in res.plans:
            r.append("PLAN_MANQUANT")
    return r


def evaluer(res: ResultatImport, publies: Optional[Dict[str, str]] = None, *,
            autoriser_fictif: bool = False) -> Dict[str, Evaluation]:
    """`publies` : {contenu_id: empreinte publiée} (journal). Renvoie l'évaluation de chaque contenu."""
    publies = publies or {}
    out: Dict[str, Evaluation] = {}
    for contenu, est_exo in [*((e, True) for e in res.exercices), *((q, False) for q in res.quiz)]:
        raisons = tuple(sorted(set(_raisons(res, contenu, est_exercice=est_exo, autoriser_fictif=autoriser_fictif))))
        emp = empreinte_contenu(contenu)
        if raisons:
            etat = EtatPublication.BLOQUE
        elif publies.get(contenu.id) == emp:
            etat = EtatPublication.PUBLISHED
        else:
            etat = EtatPublication.READY_FOR_PUBLICATION
        out[contenu.id] = Evaluation(contenu.id, etat, raisons, emp)
    return out


class RegistrePublication:
    """Journal append-only des décisions humaines de publication, à côté du dépôt de contenu."""

    def __init__(self, racine_depot: Path):
        self.fichier = Path(racine_depot) / "PUBLICATIONS.jsonl"

    def publies(self) -> Dict[str, str]:
        etat: Dict[str, str] = {}
        if not self.fichier.exists():
            return etat
        for ligne in self.fichier.read_text(encoding="utf-8").splitlines():
            try:
                e = json.loads(ligne)
            except ValueError:
                raise PublicationRefusee("journal_de_publication_corrompu")
            if e.get("action") == "publier":
                etat[e["contenu_id"]] = e["empreinte"]
            elif e.get("action") == "retirer":
                etat.pop(e["contenu_id"], None)
        return etat

    def _ecrire(self, evenement: dict) -> None:
        self.fichier.parent.mkdir(parents=True, exist_ok=True)
        with self.fichier.open("a", encoding="utf-8") as f:
            f.write(json.dumps(evenement, sort_keys=True, ensure_ascii=False) + "\n")

    def publier(self, res: ResultatImport, contenu_id: str, operateur: str, *, autoriser_fictif: bool = False) -> Evaluation:
        if not _OPERATEUR.fullmatch(operateur or ""):
            raise PublicationRefusee("operateur_invalide")
        ev = evaluer(res, self.publies(), autoriser_fictif=autoriser_fictif).get(contenu_id)
        if ev is None:
            raise PublicationRefusee("contenu_inconnu")
        if ev.etat == EtatPublication.PUBLISHED:
            return ev
        if ev.etat != EtatPublication.READY_FOR_PUBLICATION:
            raise PublicationRefusee("contenu_non_pret:" + ",".join(ev.raisons))
        self._ecrire({"action": "publier", "contenu_id": contenu_id, "empreinte": ev.empreinte,
                      "lot": res.manifest.get("lot_id"), "operateur": operateur,
                      "date": _dt.datetime.now(_dt.timezone.utc).isoformat()})
        return ev._replace(etat=EtatPublication.PUBLISHED)

    def retirer(self, contenu_id: str, operateur: str) -> None:
        if not _OPERATEUR.fullmatch(operateur or ""):
            raise PublicationRefusee("operateur_invalide")
        self._ecrire({"action": "retirer", "contenu_id": contenu_id, "operateur": operateur,
                      "date": _dt.datetime.now(_dt.timezone.utc).isoformat()})


def catalogue_publie(res: ResultatImport, registre: RegistrePublication, *, autoriser_fictif: bool = False):
    """Catalogue du tuteur restreint aux exercices PUBLISHED (et toujours revalidés)."""
    from app.api.v1.tutorat.contenu import CatalogueTutorat

    evals = evaluer(res, registre.publies(), autoriser_fictif=autoriser_fictif)
    ok = {i for i, e in evals.items() if e.etat == EtatPublication.PUBLISHED}
    exos = [e for e in res.exercices if e.id in ok]
    return CatalogueTutorat(res.referentiel, exos, {k: v for k, v in res.plans.items() if k in ok},
                            autoriser_fictif=autoriser_fictif)
