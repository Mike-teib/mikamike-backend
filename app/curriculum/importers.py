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
  - checkpoint : l'état DONE/FAILED de chaque fichier est consigné atomiquement ; à la
    reprise, un fichier DONE à empreinte identique est marqué `reprise=true` (il est
    RELU pour reconstruire le référentiel en mémoire — l'import est pur, sans cache) ;
    un checkpoint illisible est réinitialisé (jamais source de vérité) ;
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
from typing import Any, Dict, FrozenSet, Iterator, List, Optional, Tuple

from pydantic import ValidationError

from app.curriculum.exercices import Exercice
from app.curriculum.integrite import RapportIntegrite, verifier_integrite
from app.curriculum.model import Notion, Referentiel
from app.curriculum.pedagogie.tuteur import PlanGuidage
from app.curriculum.quiz import QuestionQuiz
from app.curriculum.structure import Anomalie

NOM_MANIFEST = "IMPORT_MANIFEST.json"
TYPES = ("referentiel", "registre_notions", "mapping_notion_chapitre", "index_contenus", "opaque")
# Manifest v2 (IMPORT_CONTRACT.md) : types supplémentaires.
TYPES_V2 = TYPES + ("plans_guidage", "source_document", "manifest_sha256")
# Rôle = provenance de l'artefact dans le chantier local ; il restreint les types admis.
_CANONIQUES = frozenset({"referentiel", "registre_notions", "mapping_notion_chapitre", "index_contenus"})
ROLES: Dict[str, FrozenSet[str]] = {
    "programme_officiel": frozenset({"source_document"}),
    "source_pdf": frozenset({"source_document"}),
    "referentiel": frozenset({"referentiel"}),
    "registre_notions": frozenset({"registre_notions"}),
    "mapping_chapitre_notion": frozenset({"mapping_notion_chapitre"}),
    "index_exercices": frozenset({"index_contenus"}),
    "index_quiz": frozenset({"index_contenus"}),
    "plans_guidage": frozenset({"plans_guidage"}),
    "manifest_sha256": frozenset({"manifest_sha256"}),
    "rapport": frozenset({"opaque"}),
    # Artefacts du chantier local : OPAQUES tant qu'aucun adaptateur n'est écrit à partir
    # d'échantillons réels, ou déjà CONVERTIS par le producteur vers un type canonique.
    **{r: _CANONIQUES | {"opaque"} for r in ("c02", "c02_6", "c02_6_1", "m01_maths_cycle3", "extraction_v3")},
}
MAX_DOCUMENT_OCTETS = 500 * 1024 * 1024  # un document source est haché en flux, jamais chargé
MAX_LIGNE = 1_000_000  # caractères par ligne JSONL (lecture bornée : jamais de ligne géante en RAM)
MAX_JSON_OCTETS = 50 * 1024 * 1024  # fichier `referentiel` (JSON monolithique)
# Erreurs de contenu hostile converties en FAILED (jamais d'exception non gérée) :
# JSON trop imbriqué (RecursionError), valeurs hors bornes, encodage invalide.
_ERREURS_CONTENU = (RecursionError, ValueError, TypeError, UnicodeDecodeError)

_CLES_PERSONNELLES = {"nom", "prenom", "email", "mail", "telephone", "tel", "adresse", "date_naissance",
                      "eleve_nom", "nom_eleve", "prenom_eleve", "ip", "photo"}
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_TEL = re.compile(r"(?<![\w.])(?:\+33\s?|0)[1-9](?:[\s.\-]?\d{2}){4}(?![\w.])")


class ErreurImport(ValueError):
    pass


def sha256_fichier(chemin: Path) -> str:
    h = hashlib.sha256()
    with chemin.open("rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def _cles_recursives(obj: Any) -> Iterator[str]:
    """Parcours ITÉRATIF (pas de récursion Python sur un JSON profondément imbriqué)."""
    pile = [obj]
    while pile:
        o = pile.pop()
        if isinstance(o, dict):
            for k, v in o.items():
                yield str(k).lower()
                pile.append(v)
        elif isinstance(o, list):
            pile.extend(o)


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
        num = 0
        while True:
            ligne = f.readline(MAX_LIGNE + 1)  # lecture BORNÉE
            if not ligne:
                break
            num += 1
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
    plans: Dict[str, PlanGuidage] = field(default_factory=dict)
    documents: Dict[str, str] = field(default_factory=dict)  # chemin -> sha256 (source_document)
    manifest: Dict[str, Any] = field(default_factory=dict)   # en-tête v2 (lot_id, producteur, date)
    integrite: Optional[RapportIntegrite] = None


def _charger_checkpoint(chemin: Optional[Path]) -> Dict[str, Dict[str, str]]:
    if chemin and chemin.exists():
        try:
            data = json.loads(chemin.read_text(encoding="utf-8"))
        except (ValueError, UnicodeDecodeError, RecursionError):
            return {}
        if isinstance(data, dict) and all(isinstance(v, dict) for v in data.values()):
            return data
    return {}


def _ecrire_checkpoint(chemin: Optional[Path], etat: Dict[str, Dict[str, str]]) -> None:
    if chemin is None:
        return
    chemin.parent.mkdir(parents=True, exist_ok=True)
    tmp = chemin.with_suffix(".tmp")
    tmp.write_text(json.dumps(etat, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    tmp.replace(chemin)  # écriture atomique


_ENTETE_V2 = {"version", "lot_id", "producteur", "date", "fichiers"}
_ENTREE_V2 = {"chemin", "sha256", "taille", "type", "role"}


def lire_manifest(dossier: Path, *, sha256_manifest: Optional[str] = None) -> List[Dict[str, Any]]:
    return lire_manifest_complet(dossier, sha256_manifest=sha256_manifest)["fichiers"]


def lire_manifest_complet(dossier: Path, *, sha256_manifest: Optional[str] = None) -> Dict[str, Any]:
    m = dossier / NOM_MANIFEST
    if not m.is_file():
        raise ErreurImport("manifest_absent")
    brut = m.read_bytes()
    if sha256_manifest is not None and hashlib.sha256(brut).hexdigest() != sha256_manifest:
        # Manifest épinglé hors bande : un manifest régénéré après falsification est refusé.
        raise ErreurImport("empreinte_manifest_differente")
    data = json.loads(brut.decode("utf-8"))
    if not isinstance(data, dict) or data.get("version") not in (1, 2) or not isinstance(data.get("fichiers"), list):
        raise ErreurImport("manifest_version_ou_format_invalide")
    v2 = data["version"] == 2
    if v2:
        if set(data) != _ENTETE_V2:
            raise ErreurImport("entete_manifest_v2_invalide")
        if sha256_manifest is None:
            raise ErreurImport("empreinte_manifest_non_epinglee")
        if not (isinstance(data["lot_id"], str) and re.fullmatch(r"[a-z0-9][a-z0-9\-]{2,63}", data["lot_id"])):
            raise ErreurImport("lot_id_invalide")
        if not (isinstance(data["date"], str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", data["date"])):
            raise ErreurImport("date_invalide")
        if not (isinstance(data["producteur"], str) and 1 <= len(data["producteur"]) <= 200):
            raise ErreurImport("producteur_invalide")
    racine = dossier.resolve()
    vus = set()
    for f in data["fichiers"]:
        attendues = _ENTREE_V2 if v2 else {"chemin", "sha256", "type"}
        if not isinstance(f, dict) or set(f) != attendues \
                or not all(isinstance(f[k], str) for k in attendues - {"taille"}):
            raise ErreurImport("entree_manifest_invalide")
        if v2 and not (isinstance(f["taille"], int) and not isinstance(f["taille"], bool) and f["taille"] >= 0):
            raise ErreurImport("taille_manifest_invalide")
        if f["type"] not in (TYPES_V2 if v2 else TYPES):
            raise ErreurImport(f"type_inconnu:{f['type']}")
        if v2 and f["type"] not in ROLES.get(f["role"], frozenset()):
            raise ErreurImport(f"role_incompatible:{f['role']}/{f['type']}")
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
    return data


def importer(
    dossier: Path,
    *,
    checkpoint: Optional[Path] = None,
    sha256_manifest: Optional[str] = None,
    rentree: Optional[int] = None,
    autoriser_fictif: bool = False,
) -> ResultatImport:
    """
    Import fail-closed. `sha256_manifest` : empreinte du manifest communiquée HORS BANDE
    (obligatoire en v2). `rentree` : contrôle que chaque notion relève d'un programme en
    vigueur. Statut VALIDATED seulement si l'intégrité croisée est démontrée.
    """
    res = ResultatImport()
    try:
        entete = lire_manifest_complet(dossier, sha256_manifest=sha256_manifest)
        entrees = entete["fichiers"]
    except (ErreurImport, *_ERREURS_CONTENU) as exc:
        res.statut = "FAILED"
        res.fichiers[NOM_MANIFEST] = {"etat": "FAILED", "raison": str(exc)}
        return res
    v2 = entete["version"] == 2
    res.manifest = {k: entete[k] for k in ("version", "lot_id", "producteur", "date") if k in entete}
    shas_lot = {e["chemin"]: e["sha256"] for e in entrees}

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
            if v2 and chemin.stat().st_size != e["taille"]:
                raise ErreurImport("taille_differente")
            deja = etat.get(cle, {})
            reprise = deja.get("etat") == "DONE" and deja.get("sha256") == reel

            if type_ == "referentiel":
                if chemin.stat().st_size > MAX_JSON_OCTETS:
                    raise ErreurImport("referentiel_trop_volumineux")
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
            elif type_ == "plans_guidage":
                lot_p: Dict[str, PlanGuidage] = {}
                for num, obj in _lignes_jsonl(chemin):
                    if not isinstance(obj, dict) or set(obj) != {"exercice_id", "plan"} \
                            or not isinstance(obj["exercice_id"], str):
                        raise ErreurImport(f"ligne_{num}_plan_invalide")
                    if obj["exercice_id"] in lot_p or obj["exercice_id"] in res.plans:
                        raise ErreurImport(f"ligne_{num}_plan_duplique")
                    lot_p[obj["exercice_id"]] = PlanGuidage.model_validate(obj["plan"])
                res.plans.update(lot_p)
            elif type_ == "source_document":
                # Document officiel (PDF…) : haché en flux (déjà fait), JAMAIS chargé ni interprété.
                if chemin.stat().st_size > MAX_DOCUMENT_OCTETS:
                    raise ErreurImport("document_trop_volumineux")
                res.documents[cle] = reel
            elif type_ == "manifest_sha256":
                _verifier_manifest_sha256(chemin, shas_lot)
                res.opaques.append({"chemin": cle, "sha256": reel, "statut": "MANIFEST_VERIFIE"})
            else:  # opaque
                res.opaques.append({"chemin": cle, "sha256": reel, "statut": "OPAQUE_A_MAPPER",
                                    **({"role": e["role"]} if v2 else {})})

            res.fichiers[cle] = {"etat": "DONE", "sha256": reel, "reprise": str(reprise).lower()}
            etat[cle] = {"etat": "DONE", "sha256": reel}
        except (ErreurImport, ValidationError, *_ERREURS_CONTENU) as exc:
            if isinstance(exc, ValidationError):
                raison = f"schema_invalide:{exc.error_count()}_erreur(s)"
            elif isinstance(exc, RecursionError):
                raison = "json_trop_imbrique"
            else:
                raison = (str(exc).splitlines() or [type(exc).__name__])[0][:200]
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
    cibles: Dict[str, str] = {}
    for nid, cid in mappings:
        if nid in cibles and cibles[nid] != cid:
            res.anomalies.append(Anomalie("MAPPING_CONTRADICTOIRE", nid, f"{cibles[nid]} / {cid}"))
        cibles.setdefault(nid, cid)
    for nid, cid in mappings:
        if nid not in toutes:
            res.anomalies.append(Anomalie("MAPPING_NOTION_INCONNUE", nid, cid))
        elif cid not in chap_ids:
            res.anomalies.append(Anomalie("MAPPING_CHAPITRE_INCONNU", nid, cid))
        else:
            toutes[nid] = toutes[nid].model_copy(update={"chapitre_id": cid})

    ref = base.model_copy(update={"notions": tuple(toutes[k] for k in sorted(toutes))})
    res.referentiel = ref
    # Intégrité CROISÉE (structure + preuves + textes + contenus + plans + documents sources).
    res.integrite = verifier_integrite(
        ref, res.exercices, res.quiz, plans=res.plans,
        documents_sha256=set(res.documents.values()) if v2 else None,
        rentree=rentree, autoriser_fictif=autoriser_fictif,
    )
    res.anomalies = sorted(set(res.anomalies) | set(res.integrite.anomalies))
    res.statut = "VALIDATED" if not res.anomalies else "REJECTED"
    return res


def _verifier_manifest_sha256(chemin: Path, shas_lot: Dict[str, str]) -> None:
    """Manifest « HASH  chemin » (format SHA256_*.txt) : chaque entrée doit être un fichier DU LOT
    à l'empreinte identique (corpus source complet et intact)."""
    n = 0
    for num, ligne in enumerate(chemin.read_text(encoding="utf-8-sig").splitlines(), start=1):
        if not ligne.strip():
            continue
        h, _, cible = ligne.strip().partition("  ")
        cible = cible.replace("\\", "/").strip()
        if not re.fullmatch(r"[0-9a-fA-F]{64}", h) or not cible:
            raise ErreurImport(f"manifest_sha256_ligne_{num}_invalide")
        if shas_lot.get(cible) != h.lower():
            raise ErreurImport(f"manifest_sha256_incoherent:{cible}")
        n += 1
    if n == 0:
        raise ErreurImport("manifest_sha256_vide")


def ecrire_manifest(dossier: Path, types: Dict[str, str]) -> Path:
    """Utilitaire (côté producteur) : génère le manifest à partir des fichiers présents."""
    fichiers = [
        {"chemin": chemin, "sha256": sha256_fichier(dossier / chemin), "type": type_}
        for chemin, type_ in sorted(types.items())
    ]
    m = dossier / NOM_MANIFEST
    m.write_text(json.dumps({"version": 1, "fichiers": fichiers}, indent=2, ensure_ascii=False), encoding="utf-8")
    return m


def ecrire_manifest_v2(dossier: Path, fichiers: Dict[str, Tuple[str, str]], *, lot_id: str,
                       producteur: str, date: str) -> str:
    """
    Côté producteur : `fichiers` = {chemin: (type, role)}. Écrit le manifest v2 et renvoie son
    SHA-256, à transmettre HORS BANDE (canal distinct du lot) à la personne qui importe.
    """
    entrees = [
        {"chemin": c, "sha256": sha256_fichier(dossier / c), "taille": (dossier / c).stat().st_size,
         "type": t, "role": r}
        for c, (t, r) in sorted(fichiers.items())
    ]
    m = dossier / NOM_MANIFEST
    m.write_text(json.dumps({"version": 2, "lot_id": lot_id, "producteur": producteur, "date": date,
                             "fichiers": entrees}, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return sha256_fichier(m)
