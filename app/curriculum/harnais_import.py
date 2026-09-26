"""
harnais_import.py — Harnais de test du pipeline d'import avec des lots SYNTHÉTIQUES.

⚠ Les artefacts réels (C02, C02-6, C02-6.1, M01, Extraction V3, PDF BO/Éduscol) ne sont PAS
disponibles et ne sont PAS inventés ici. Ce module fabrique des lots **synthétiques**
représentatifs de la FORME attendue par IMPORT_CONTRACT.md (rôles, types, manifests, empreintes)
pour éprouver le pipeline de bout en bout. Tout y est marqué `[SYNTHÉTIQUE]`, la source est
`fictive=True` : ces données ne peuvent jamais devenir PROVEN en production.

Pipeline éprouvé, dans l'ordre du manifest :
  manifest → C02 → C02-6 → C02-6.1 → M01 → Extraction V3 → PDF source → provenance → mapping → backlog

Défauts injectables (`defauts`) : sha_incorrect, fichier_manquant, fichier_non_liste,
doublon_notion, doublon_manifest, doublon_contenu, mauvais_role, document_altere,
provenance_falsifiee, mapping_contradictoire, mapping_notion_inconnue, json_invalide.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from app.curriculum.backlog import calculer_backlog
from app.curriculum.ids import sha256_octets, sha256_texte
from app.curriculum.importers import ErreurImport, ResultatImport, ecrire_manifest_v2, importer, lire_manifest_complet
from app.curriculum.model import (
    Chapitre,
    Domaine,
    Matiere,
    Niveau,
    Notion,
    Preuve,
    Programme,
    Referentiel,
    SourceOfficielle,
    StatutPreuve,
    StatutTexte,
    Theme,
)

MARQUE = "[SYNTHÉTIQUE]"
SOURCE_ID = "src:synthetique:bo-maths-cycle3"
PROG_ID = "prog:synthetique:mathematiques:cycle3:2025"
DEFAUTS = frozenset({
    "sha_incorrect", "fichier_manquant", "fichier_non_liste", "doublon_notion", "doublon_manifest",
    "doublon_contenu", "mauvais_role", "document_altere", "provenance_falsifiee", "mapping_contradictoire",
    "mapping_notion_inconnue", "json_invalide",
})
# Ordre du pipeline (= ordre des entrées du manifest).
ETAPES = ("c02", "c02_6", "c02_6_1", "m01_maths_cycle3", "extraction_v3", "source_pdf", "referentiel",
          "mapping_chapitre_notion", "manifest_sha256")

_VERBES = ("Comparer", "Ranger", "Encadrer", "Additionner", "Soustraire", "Multiplier", "Diviser", "Estimer",
           "Représenter", "Décomposer")
_OBJETS = ("des nombres entiers", "des fractions simples", "des nombres décimaux", "des longueurs",
           "des aires de rectangles", "des durées", "des angles", "des masses", "des contenances", "des périmètres")


def pdf_synthetique(n_pages: int = 3, graine: str = "") -> bytes:
    """Octets d'un « PDF » synthétique (jamais interprété par l'import : seulement haché)."""
    corps = "".join(f"% {MARQUE} page {p} {graine}\n" for p in range(1, n_pages + 1))
    return f"%PDF-1.4\n{corps}%%EOF\n".encode("utf-8")


def _extrait(i: int) -> str:
    # L'extrait verbatim CONTIENT le texte de la notion (sinon la preuve est AMBIGUOUS).
    return f"{_texte(i)} Suite synthétique du paragraphe, page {1 + i % 3}."


def _texte(i: int) -> str:
    return f"{MARQUE} {_VERBES[i % 10]} {_OBJETS[(i // 10) % 10]}, repère {i}."


def referentiel_structure(sha_pdf: str, n_chapitres: int) -> Referentiel:
    src = SourceOfficielle(id=SOURCE_ID, titre=f"{MARQUE} Programme de démonstration",
                           editeur="MikaMike — harnais de test", url="https://example.invalid/synthetique.pdf",
                           reference="HARNAIS_SYNTHETIQUE", date_publication="2026-09-01",
                           sha256_document=sha_pdf, fictive=True)
    prog = Programme(id=PROG_ID, source_id=SOURCE_ID, matiere=Matiere.MATHEMATIQUES,
                     niveaux=(Niveau.CM1, Niveau.CM2, Niveau.SIXIEME), titre=f"{MARQUE} Mathématiques cycle 3",
                     rentree_debut=2025)
    dom = Domaine(id="dom:synthetique:nombres", programme_id=PROG_ID, titre=f"{MARQUE} Nombres", ordre=1)
    th = Theme(id="theme:synthetique:calcul", programme_id=PROG_ID, domaine_id=dom.id,
               titre=f"{MARQUE} Calcul", ordre=1)
    chaps = tuple(Chapitre(id=f"chap:synthetique:c{k}", programme_id=PROG_ID, theme_id=th.id,
                           niveau=Niveau.SIXIEME, titre=f"{MARQUE} Chapitre {k}", ordre=k)
                  for k in range(n_chapitres))
    return Referentiel(sources=(src,), programmes=(prog,), domaines=(dom,), themes=(th,), chapitres=chaps)


def notion_synthetique(i: int, *, falsifiee: bool = False) -> Notion:
    extrait = _extrait(i)
    return Notion(
        id=f"notion:synthetique:n{i}", programme_id=PROG_ID, chapitre_id=None, niveau=Niveau.SIXIEME,
        matiere=Matiere.MATHEMATIQUES, texte=_texte(i), statut_texte=StatutTexte.TEXT_EXACT,
        preuve=Preuve(source_id=SOURCE_ID, document="sources/bo_synthetique.pdf",
                      url="https://example.invalid/synthetique.pdf", page=1 + i % 3, extrait=extrait,
                      sha256_extrait=sha256_texte(extrait + (" altéré" if falsifiee else "")),
                      statut=StatutPreuve.PROVEN, date_verification="2026-09-26"),
    )


@dataclass
class Lot:
    dossier: Path
    sha_manifest: str
    n_notions: int
    defauts: frozenset = frozenset()


def _ecrire_jsonl(chemin: Path, lignes: Iterable[str]) -> None:
    # Écriture en flux : aucune liste complète en mémoire, même pour 100 000 notions.
    with chemin.open("w", encoding="utf-8") as f:
        for ligne in lignes:
            f.write(ligne)
            f.write("\n")


def generer_lot(dossier: Path, *, n_notions: int = 12, n_chapitres: int = 3, defauts: Iterable[str] = (),
                lot_id: str = "lot-synthetique-1", graine: str = "") -> Lot:
    defauts = frozenset(defauts)
    inconnus = defauts - DEFAUTS
    if inconnus:
        raise ValueError(f"defauts_inconnus:{sorted(inconnus)}")
    dossier.mkdir(parents=True, exist_ok=True)
    (dossier / "sources").mkdir(exist_ok=True)
    pdf = pdf_synthetique(graine=graine)
    (dossier / "sources" / "bo_synthetique.pdf").write_bytes(pdf)
    ref = referentiel_structure(sha256_octets(pdf), n_chapitres)
    (dossier / "referentiel.json").write_text(ref.model_dump_json(), "utf-8")

    # C02 / C02-6 / Extraction V3 : format interne inconnu ⇒ OPAQUES (empreinte seulement).
    (dossier / "C02").mkdir(exist_ok=True)
    (dossier / "C02" / "resultats.bin").write_bytes(f"{MARQUE} C02 opaque {graine}".encode())
    (dossier / "C02-6").mkdir(exist_ok=True)
    (dossier / "C02-6" / "resultats.bin").write_bytes(f"{MARQUE} C02-6 opaque {graine}".encode())
    (dossier / "ExtractionV3").mkdir(exist_ok=True)
    (dossier / "ExtractionV3" / "rapport.json").write_text(
        "{pas du json" if "json_invalide" in defauts else json.dumps({"marque": MARQUE, "pages": 3}, ensure_ascii=False), "utf-8")
    # C02-6.1 : supposé CONVERTI par le producteur en index de contenus (vide ici : pas d'exercice
    # synthétique « prouvé » — le harnais éprouve le pipeline, pas la pédagogie).
    lignes_c0261 = []
    if "doublon_contenu" in defauts:
        ex = {"kind": "quiz", "data": {"id": "quiz:synthetique:1"}}
        lignes_c0261 = [json.dumps(ex), json.dumps(ex)]
    _ecrire_jsonl(dossier / "C02-6.1.jsonl", lignes_c0261)

    # M01 : registre de notions (converti), en flux.
    def notions():
        for i in range(n_notions):
            yield notion_synthetique(i, falsifiee="provenance_falsifiee" in defauts and i == 0).model_dump_json()
        if "doublon_notion" in defauts:
            yield notion_synthetique(0).model_dump_json()
    _ecrire_jsonl(dossier / "M01_notions.jsonl", notions())

    def mappings():
        for i in range(n_notions):
            yield json.dumps({"notion_id": f"notion:synthetique:n{i}", "chapitre_id": f"chap:synthetique:c{i % n_chapitres}"})
        if "mapping_contradictoire" in defauts:
            yield json.dumps({"notion_id": "notion:synthetique:n0", "chapitre_id": f"chap:synthetique:c{1 % n_chapitres}"
                              if n_chapitres > 1 else "chap:synthetique:autre"})
        if "mapping_notion_inconnue" in defauts:
            yield json.dumps({"notion_id": "notion:synthetique:fantome", "chapitre_id": "chap:synthetique:c0"})
    _ecrire_jsonl(dossier / "mapping.jsonl", mappings())

    (dossier / "SHA256_SOURCE.txt").write_text(f"{sha256_octets(pdf)}  sources/bo_synthetique.pdf\n", "utf-8")

    fichiers: Dict[str, Tuple[str, str]] = {
        "C02/resultats.bin": ("opaque", "c02"),
        "C02-6/resultats.bin": ("opaque", "c02_6"),
        "C02-6.1.jsonl": ("index_contenus", "c02_6_1"),
        "M01_notions.jsonl": ("registre_notions", "m01_maths_cycle3"),
        "ExtractionV3/rapport.json": ("referentiel" if "json_invalide" in defauts else "opaque", "extraction_v3"),
        "sources/bo_synthetique.pdf": ("source_document", "source_pdf"),
        "referentiel.json": ("referentiel", "referentiel"),
        "mapping.jsonl": ("mapping_notion_chapitre", "mapping_chapitre_notion"),
        "SHA256_SOURCE.txt": ("manifest_sha256", "manifest_sha256"),
    }
    if "mauvais_role" in defauts:
        fichiers["sources/bo_synthetique.pdf"] = ("source_document", "plans_guidage")
    sha = ecrire_manifest_v2(dossier, fichiers, lot_id=lot_id, producteur=f"{MARQUE} harnais", date="2026-09-26",
                             trier=False)

    # Défauts appliqués APRÈS le manifest (falsification / perte en transit).
    if "doublon_manifest" in defauts:
        m = json.loads((dossier / "IMPORT_MANIFEST.json").read_text("utf-8"))
        m["fichiers"].append(dict(m["fichiers"][0]))
        brut = json.dumps(m, indent=2, sort_keys=True).encode("utf-8")
        (dossier / "IMPORT_MANIFEST.json").write_bytes(brut)
        sha = sha256_octets(brut)
    if "sha_incorrect" in defauts:
        (dossier / "C02" / "resultats.bin").write_bytes(f"{MARQUE} C02 MODIFIÉ".encode())
    if "document_altere" in defauts:
        with (dossier / "sources" / "bo_synthetique.pdf").open("ab") as f:
            f.write(b"% ajout apres signature\n")
    if "fichier_manquant" in defauts:
        (dossier / "mapping.jsonl").unlink()
    if "fichier_non_liste" in defauts:
        (dossier / "intrus.txt").write_text("non listé", "utf-8")
    return Lot(dossier, sha, n_notions, defauts)


# --------------------------------------------------------------------------- #
# Exécution du pipeline, étape par étape
# --------------------------------------------------------------------------- #
@dataclass
class RapportPipeline:
    statut: str
    etapes: List[Tuple[str, str, str]] = field(default_factory=list)  # (étape, état, détail)
    resultat: Optional[ResultatImport] = None
    backlog: Optional[dict] = None

    def etat(self, etape: str) -> Optional[str]:
        return next((e for n, e, _ in self.etapes if n == etape), None)


_CODES_PROVENANCE = ("HASH_EXTRAIT_INCOHERENT", "PREUVE_SOURCE_AUTRE_PROGRAMME", "SOURCE_DOCUMENT_ABSENT",
                     "TEXTE_DECLARE_INCOHERENT", "PREUVE")
_CODES_MAPPING = ("MAPPING_", "IMPORT_NOTION_EN_CONFLIT", "NOTION_SANS_CHAPITRE")


def executer_pipeline(dossier: Path, sha_manifest: str, *, checkpoint: Optional[Path] = None,
                      rentree: Optional[int] = 2026, autoriser_fictif: bool = True) -> RapportPipeline:
    rap = RapportPipeline(statut="PENDING")
    try:
        entete = lire_manifest_complet(dossier, sha256_manifest=sha_manifest)
        rap.etapes.append(("manifest", "OK", f"{len(entete['fichiers'])} fichiers"))
    except (ErreurImport, ValueError, RecursionError) as exc:
        rap.etapes.append(("manifest", "FAILED", str(exc)[:200]))
    res = importer(dossier, checkpoint=checkpoint, sha256_manifest=sha_manifest, rentree=rentree,
                   autoriser_fictif=autoriser_fictif)
    rap.resultat = res
    if rap.etat("manifest") == "OK":
        par_role = {f["role"]: f["chemin"] for f in entete["fichiers"]}
        for etape in ETAPES:
            chemin = par_role.get(etape)
            info = res.fichiers.get(chemin, {}) if chemin else {}
            rap.etapes.append((etape, info.get("etat", "ABSENT"), info.get("raison", chemin or "")))
    if res.statut == "FAILED":
        rap.statut = "FAILED"
        return rap
    codes = [a.code for a in res.anomalies]
    prov = [c for c in codes if c.startswith(_CODES_PROVENANCE)]
    mapp = [c for c in codes if c.startswith(_CODES_MAPPING)]
    rap.etapes.append(("provenance", "OK" if not prov else "ANOMALIE", ",".join(sorted(set(prov)))))
    rap.etapes.append(("mapping", "OK" if not mapp else "ANOMALIE", ",".join(sorted(set(mapp)))))
    rap.backlog = calculer_backlog(res.referentiel, res.exercices, res.quiz, autoriser_fictif=autoriser_fictif,
                                   integrite=res.integrite)
    rap.etapes.append(("backlog", "OK", json.dumps(rap.backlog["total"], sort_keys=True)))
    rap.statut = res.statut
    return rap
