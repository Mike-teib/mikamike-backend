"""
Modèle canonique (invariants de provenance) et chaîne de preuve à partir d'un PDF local.
Le PDF est généré dans le test (contenu [FICTIF]) : aucune source réelle, aucun réseau.
"""

import hashlib
import json

import pytest
from pydantic import ValidationError

from pedagogy.models import (
    Course,
    Cycle,
    Exercise,
    Level,
    Notion,
    NotionFile,
    OfficialSource,
    ProofStatus,
    PublicationStatus,
    QuizItem,
    ReviewStatus,
    SourceRetrieval,
    SourceType,
    Subject,
    json_schema_bundle,
    make_notion_id,
    normalize_title,
)
from pedagogy.sources import (
    ExtractionError,
    load_source_text,
    normalize_for_match,
    promote_notion,
    propose_promotions,
    register_source,
    verify_notion_against_source,
)
from pedagogy.sources_cli import main as cli


def _pdf(pages):
    """PDF minimal (texte latin-1) lisible par pypdf."""
    n = len(pages)
    font = 3 + 2 * n
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>",
            f"<< /Type /Pages /Kids [{' '.join(f'{3 + 2 * i} 0 R' for i in range(n))}] /Count {n} >>".encode()]
    for i, t in enumerate(pages):
        s = f"BT /F1 11 Tf 40 780 Td ({t}) Tj ET".encode("latin-1")
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents {4 + 2 * i} 0 R "
                    f"/Resources << /Font << /F1 {font} 0 R >> >> >>".encode())
        objs.append(b"<< /Length %d >>\nstream\n" % len(s) + s + b"\nendstream")
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    buf, offs = b"%PDF-1.4\n", []
    for i, o in enumerate(objs):
        offs.append(len(buf))
        buf += f"{i + 1} 0 obj\n".encode() + o + b"\nendobj\n"
    x = len(buf)
    buf += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    buf += b"".join(f"{o:010d} 00000 n \n".encode() for o in offs)
    buf += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{x}\n%%EOF\n".encode()
    return buf


PAGES = [
    "[FICTIF] Programme de demonstration - sommaire",
    "[FICTIF] Utiliser les puissances de 10 pour ecrire un nombre",
    "[FICTIF] Theoreme de Pythagore : calculer une longueur",
]


def _candidate(title="Puissances de 10", **kw) -> Notion:
    base = dict(
        notion_id=make_notion_id(Subject.MATHS, Level.QUATRIEME, "NC", title),
        subject=Subject.MATHS, level=Level.QUATRIEME, cycle=Cycle.CYCLE_4, school_year="2025-2026",
        official_program_version="[FICTIF] v1", domain="Nombres et calculs", domain_code="NC",
        chapter="Puissances", title=title, normalized_title=normalize_title(title), difficulty=2,
        source_type=SourceType.CANDIDATE_UNVERIFIED, source_id="SRC-FICTIF",
        source_title="[FICTIF] programme", source_url_or_ref="[FICTIF]",
    )
    base.update(kw)
    return Notion(**base)


@pytest.fixture()
def repo(tmp_path):
    pdf = tmp_path / "officiel.pdf"
    pdf.write_bytes(_pdf(PAGES))
    src = OfficialSource(
        source_id="SRC-FICTIF", source_type=SourceType.OFFICIAL_BO, title="[FICTIF] programme",
        publisher="[FICTIF]", reference="[FICTIF] BO", subjects=(Subject.MATHS,), levels=(Level.QUATRIEME,),
        school_year_start="2020-2021", local_path="officiel.pdf",
    )
    src = register_source(src, tmp_path)
    return tmp_path, src, load_source_text(src, tmp_path)


# --------------------------------------------------------------------------- #
# Invariants du modèle
# --------------------------------------------------------------------------- #
def test_id_stable_et_titre_normalise():
    assert make_notion_id(Subject.MATHS, Level.QUATRIEME, "NC", "Équations du premier degré") == \
        "MATHS.4E.NC.equations-du-premier-degre"
    assert normalize_title("  Théorème  de Pythagore. ") == "théorème de pythagore"


def test_candidat_non_prouve_valide_et_non_eligible():
    n = _candidate()
    assert n.proof_status == ProofStatus.UNPROVEN and not n.eligible_for_content


def test_libelle_officiel_interdit_sur_notion_non_prouvee():
    with pytest.raises(ValidationError, match="libelle_officiel_sur_notion_non_prouvee"):
        _candidate(official_wording="texte prétendument officiel")


@pytest.mark.parametrize("champ", ["source_id", "source_page_or_section", "official_wording", "source_sha256"])
def test_preuve_officielle_incomplete_refusee(champ):
    complet = dict(source_type=SourceType.OFFICIAL_BO, source_id="SRC-FICTIF", source_page_or_section="2",
                   official_wording="[FICTIF] Utiliser les puissances de 10", source_sha256="a" * 64,
                   proof_status=ProofStatus.PROVEN_OFFICIAL)
    _candidate(**complet)
    complet[champ] = None
    with pytest.raises(ValidationError, match="preuve_officielle_incomplete"):
        _candidate(**complet)


def test_source_candidate_ne_peut_pas_etre_prouvee():
    with pytest.raises(ValidationError, match="source_officielle"):
        _candidate(source_page_or_section="2", official_wording="x", source_sha256="a" * 64,
                   proof_status=ProofStatus.PROVEN_OFFICIAL)


@pytest.mark.parametrize("kw,msg", [
    (dict(cycle=Cycle.LYCEE_GT), "cycle_incoherent"),
    (dict(notion_id="MATHS.4E.GM.puissances-de-10"), "notion_id_incoherent"),
    (dict(normalized_title="autre"), "normalized_title_incoherent"),
    (dict(publication_status=PublicationStatus.PUBLISHED), "publication_sans_preuve"),
    (dict(proof_status=ProofStatus.PROVEN_INTERNAL), "preuve_interne_sans_source_interne"),
])
def test_invariants_notion(kw, msg):
    with pytest.raises(ValidationError, match=msg):
        _candidate(**kw)


def test_matiere_absente_a_ce_niveau():
    with pytest.raises(ValidationError, match="matiere_absente_a_ce_niveau"):
        Notion(notion_id="PC.6E.MAT.etats-de-la-matiere", subject=Subject.PHYSIQUE_CHIMIE, level=Level.SIXIEME,
               cycle=Cycle.CYCLE_3, school_year="2025-2026", official_program_version="xx", domain="Matière",
               domain_code="MAT", chapter="xx", title="États de la matière",
               normalized_title=normalize_title("États de la matière"), difficulty=1,
               source_type=SourceType.CANDIDATE_UNVERIFIED, source_title="xx", source_url_or_ref="xx")


def test_publication_exige_preuve_et_revue():
    ok = dict(source_type=SourceType.OFFICIAL_BO, source_id="S", source_page_or_section="2",
              official_wording="w", source_sha256="a" * 64, proof_status=ProofStatus.PROVEN_OFFICIAL,
              publication_status=PublicationStatus.PUBLISHED)
    with pytest.raises(ValidationError):
        _candidate(**ok)
    assert _candidate(**ok, review_status=ReviewStatus.APPROVED).publication_status == PublicationStatus.PUBLISHED


def test_fichier_de_notions_homogene():
    n = _candidate()
    NotionFile(subject=Subject.MATHS, level=Level.QUATRIEME, generated_by="test", disclaimer="[FICTIF] test", notions=(n,))
    with pytest.raises(ValidationError, match="notion_id_duplique"):
        NotionFile(subject=Subject.MATHS, level=Level.QUATRIEME, generated_by="test", disclaimer="[FICTIF] test", notions=(n, n))
    with pytest.raises(ValidationError, match="notion_hors_fichier"):
        NotionFile(subject=Subject.MATHS, level=Level.TROISIEME, generated_by="test", disclaimer="[FICTIF] test", notions=(n,))
    with pytest.raises(ValidationError, match="notion_hors_fichier"):
        NotionFile(subject=Subject.MATHS, level=Level.QUATRIEME, course=Course.SPECIALITE, generated_by="test",
                   disclaimer="[FICTIF] test", notions=(n,))


def test_source_recuperee_exige_fichier_et_empreinte():
    with pytest.raises(ValidationError, match="source_recuperee_sans_fichier"):
        OfficialSource(source_id="SRC-X", source_type=SourceType.OFFICIAL_BO, title="xxx", publisher="xx",
                       subjects=(Subject.MATHS,), levels=(Level.SIXIEME,), school_year_start="2020-2021",
                       retrieval=SourceRetrieval.RETRIEVED)


def test_schemas_json_exportables():
    bundle = json_schema_bundle()
    assert set(bundle) == {"Notion", "NotionFile", "OfficialSource", "Exercise", "QuizItem"}
    json.dumps(bundle)
    assert Exercise and QuizItem


# --------------------------------------------------------------------------- #
# Chaîne de preuve
# --------------------------------------------------------------------------- #
def test_normalisation_typographique_sans_perte():
    assert normalize_for_match("Théorème de Pytha-\ngore  l’hypoténuse ﬁnale") == "théorème de pythagore l'hypoténuse finale"
    assert normalize_for_match("10^{-3} et 1/10") == "10^{-3} et 1/10"


def test_enregistrement_calcule_sha256(repo):
    root, src, _ = repo
    assert src.sha256 == hashlib.sha256((root / "officiel.pdf").read_bytes()).hexdigest()
    assert src.retrieval == SourceRetrieval.RETRIEVED


def test_fichier_altere_refuse(repo):
    root, src, _ = repo
    (root / "officiel.pdf").write_bytes(_pdf(PAGES + ["ajout"]))
    with pytest.raises(ExtractionError, match="sha256_different"):
        load_source_text(src, root)


def test_proposition_puis_promotion_explicite(repo):
    _, src, st = repo
    n = _candidate(title="Puissances de 10")
    props = propose_promotions([n], {src.source_id: st})
    assert [(p.notion_id, p.pages) for p in props] == [(n.notion_id, [2])]
    promu = promote_notion(n, st, 2, "[FICTIF] Utiliser les puissances de 10")
    assert promu.proof_status == ProofStatus.PROVEN_OFFICIAL
    assert promu.official_wording == "[FICTIF] Utiliser les puissances de 10"  # texte de la source
    assert promu.source_sha256 == src.sha256 and promu.eligible_for_content
    assert verify_notion_against_source(promu, {src.source_id: st}).status == ProofStatus.PROVEN_OFFICIAL


def test_promotion_refusee_si_extrait_absent(repo):
    _, _, st = repo
    with pytest.raises(ValueError, match="extrait_absent_de_la_page"):
        promote_notion(_candidate(), st, 2, "texte qui n'est pas dans la source")
    with pytest.raises(ValueError, match="extrait_absent_de_la_page"):
        promote_notion(_candidate(), st, 3, "[FICTIF] Utiliser les puissances de 10")  # mauvaise page


def test_preuve_recalculee_jamais_crue(repo):
    _, src, st = repo
    texts = {src.source_id: st}
    vraie = promote_notion(_candidate(), st, 2, "[FICTIF] Utiliser les puissances de 10")
    fausse_page = vraie.model_copy(update={"source_page_or_section": "3"})
    assert verify_notion_against_source(fausse_page, texts).status == ProofStatus.CONFLICT
    faux_hash = vraie.model_copy(update={"source_sha256": "b" * 64})
    assert verify_notion_against_source(faux_hash, texts).status == ProofStatus.CONFLICT
    faux_texte = vraie.model_copy(update={"official_wording": "[FICTIF] texte inventé"})
    assert verify_notion_against_source(faux_texte, texts).status == ProofStatus.UNPROVEN
    assert verify_notion_against_source(vraie, {}).status == ProofStatus.UNPROVEN


def test_source_autre_niveau_conflit(repo):
    _, src, st = repo
    vraie = promote_notion(_candidate(), st, 2, "[FICTIF] Utiliser les puissances de 10")
    autre = src.model_copy(update={"levels": (Level.TROISIEME,)})
    assert verify_notion_against_source(vraie, {src.source_id: st.__class__(autre, st.pages)}).status == ProofStatus.CONFLICT


def test_cli_status_et_verify_sur_depot_reel(capsys):
    assert cli(["status"]) == 0
    assert cli(["verify"]) == 0  # aucune notion ne se déclare PROVEN_OFFICIAL
    out = capsys.readouterr().out
    assert "SRC-C4-2020" in out
