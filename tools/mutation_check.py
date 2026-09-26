#!/usr/bin/env python3
"""
mutation_check.py — Tests de mutation ciblés (Phase 24).

Chaque mutant injecte UN bug volontaire dans le code (remplacement textuel exact),
lance la suite tests_cloud, puis restaure le fichier. Un mutant doit être TUÉ
(au moins un test échoue). Un mutant SURVIVANT signale un trou de couverture.

Usage : python -m tools.mutation_check        (≈ 1 à 2 min)
Sortie 1 si un mutant survit ou si un remplacement ne s'applique plus.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import List, NamedTuple, Tuple

RACINE = Path(__file__).resolve().parent.parent


class Mutant(NamedTuple):
    nom: str
    fichier: str
    avant: str
    apres: str
    # Suite(s) exécutée(s) pour ce mutant (défaut : tests_cloud entier).
    cibles: Tuple[str, ...] = ("tests_cloud",)


T_AUTH = ("tests_cloud/test_auth.py", "tests_cloud/test_review_session1.py")
T_API = ("tests_cloud/test_mika_api.py",)
T_IMPORT = ("tests_cloud/test_import_v2_integrite.py", "tests_cloud/test_review_session1.py")
T_ATT = ("tests_cloud/test_attaques.py", "tests_cloud/test_review_session1.py")


MUTANTS: List[Mutant] = [
    Mutant("notion_non_prouvee_acceptee", "app/curriculum/provenance.py",
           'return EvaluationPreuve(StatutPreuve.NOT_EVIDENCED, ["aucune_preuve"])',
           'return EvaluationPreuve(StatutPreuve.PROVEN, [])'),
    Mutant("source_fictive_acceptee_en_prod", "app/curriculum/provenance.py",
           "if source.fictive and not autoriser_fictif:", "if False:"),
    Mutant("texte_tronque_accepte", "app/curriculum/text_quality.py",
           '        anomalies.append("fin_tronquee")', "        pass"),
    Mutant("texte_suspect_utilisable", "app/curriculum/provenance.py",
           "if notion.statut_texte not in STATUTS_TEXTE_UTILISABLES:", "if False:"),
    Mutant("mauvais_chapitre_accepte", "app/curriculum/exercices.py",
           'raisons.append("chapitre_incoherent")', "pass"),
    Mutant("exercice_duplique_accepte", "app/curriculum/exercices.py",
           'raisons.append(f"doublon_exact:{autre.id}")', "pass"),
    Mutant("formule_cassee_acceptee", "app/curriculum/math_guard.py",
           'anomalies.append(f"FRACTION_CONVERTIE:{frac}" if convertie else f"FRACTION_PERDUE:{frac}")', "pass"),
    Mutant("quiz_ambigu_accepte", "app/curriculum/quiz.py",
           'raisons.append("DOUBLE_BONNE_REPONSE")', "pass"),
    Mutant("mauvaise_unite_acceptee", "app/curriculum/verifiers/physique.py",
           'return invalide("dimension_incorrecte")\n\n    va', 'pass\n\n    va'),
    Mutant("resultat_sans_unite_accepte", "app/curriculum/verifiers/physique.py",
           'return invalide("unite_manquante")\n    if ga.unite.dim', 'pass\n    if ga.unite.dim'),
    Mutant("reponse_vide_acceptee", "app/curriculum/verifiers/maths.py",
           'return invalide("reponse_vide")\n    try:\n        sol_att', 'return valide("vide")\n    try:\n        sol_att'),
    Mutant("niveau_incoherent_accepte", "app/curriculum/structure.py",
           'out.append(Anomalie("MAUVAIS_NIVEAU", n.id, f"{n.niveau.value} hors {prog.id}"))', "pass"),
    Mutant("valid_par_defaut", "app/curriculum/verifiers/dispatch.py",
           'return revue(f"type_verification_inconnu:{type_verification}")', 'return valide("defaut")'),
    Mutant("aide_compte_pour_maitrise", "app/curriculum/pedagogie/tuteur.py",
           'niveau_estime="ACQUIS_ASSISTE" if etat.avec_aide else "ACQUIS_AUTONOME"',
           'niveau_estime="ACQUIS_AUTONOME"'),
    Mutant("solution_donnee_immediatement", "app/curriculum/pedagogie/tuteur.py",
           "if etat.questions_posees < len(self.plan.questions_intermediaires):",
           "if False:\n            pass\n        if True:\n            return self._emettre(etat, Action.CORRECTION_COMMENTEE, self.plan.correction_commentee)\n        if False:"),
    Mutant("idor_session", "app/api/v1/session/session_manager.py",
           "    if session_obj.eleve_hmac != eleve_hmac:", "    if False:"),
    Mutant("rgpd_effacement_incomplet", "app/api/v1/rgpd/router.py",
           "TABLES_ELEVE = (TentativeExercice, EtatCompetence, TacheRappelMemoire, MikaSessionState)",
           "TABLES_ELEVE = (TentativeExercice, EtatCompetence)"),
    Mutant("repli_matiere_silencieux", "app/api/v1/parcours/curriculum_dataset.py",
           "    return list(CURRICULA_DATA.get((lvl, sub), []))",
           '    return list(CURRICULA_DATA.get((lvl, sub)) or CURRICULA_DATA[("5e", "maths")])'),
    # ---------------------------------------------------------------- session 2
    Mutant("texte_declare_cru_sur_parole", "app/curriculum/provenance.py",
           "        if recalcule not in STATUTS_TEXTE_UTILISABLES:", "        if False:"),
    Mutant("preuve_d_un_autre_programme", "app/curriculum/provenance.py",
           "notion.preuve.source_id != prog.source_id:", "False:"),
    Mutant("sympy_sans_garde_de_complexite", "app/curriculum/verifiers/maths.py",
           "    _controler_complexite(brut)\n", "\n", ("tests_cloud/test_review_session1.py",)),
    Mutant("heartbeat_proprietaire_apres_effet", "app/api/v1/session/session_manager.py",
           "        _verifier_proprietaire(session_obj, eleve_hmac)\n\n        # Vérification du timeout",
           "        # Vérification du timeout", T_ATT),
    Mutant("etat_fusionne_non_borne", "app/api/v1/session/session_manager.py",
           "            if len(fusion) > MAX_SESSION_STATE_BYTES:", "            if False:", T_ATT),
    Mutant("comprehension_non_demandee_acceptee", "app/curriculum/pedagogie/tuteur.py",
           "        if etat.termine or not etat.attend_comprehension:", "        if etat.termine:"),
    Mutant("diagnostic_non_controle", "app/curriculum/pedagogie/tuteur.py",
           "    for texte in aides + diagnostics:", "    for texte in aides:"),
    Mutant("jeton_eleve_autre_proprietaire", "app/core/auth.py",
           'if not hmac.compare_digest(qui.pseudo_id or "", pseudo_id) or action == Action.EFFACEMENT:',
           "if action == Action.EFFACEMENT:", T_AUTH),
    Mutant("parent_non_lie_autorise", "app/core/auth.py",
           "    if action not in permis or compte.role != rel:", "    if False:", T_AUTH),
    Mutant("eleve_peut_s_effacer", "app/core/auth.py",
           ' or action == Action.EFFACEMENT:', ':', T_AUTH),
    Mutant("mode_off_en_production", "app/core/auth.py",
           '    if mode == "off" and os.getenv("MIKA_ENV", "").strip().lower() in ("production", "prod"):',
           "    if False:", T_AUTH),
    Mutant("jeton_compte_accepte_comme_eleve", "app/core/auth.py",
           '        if c.get("typ") != TYP_ELEVE or c.get("role") != "eleve" or not isinstance(c.get("sub"), str):',
           '        if not isinstance(c.get("sub"), str):', T_AUTH),
    Mutant("route_sans_garde", "app/api/v1/rgpd/router.py",
           "    g.exiger(student_pseudo_id, Action.EFFACEMENT)", "    pass", T_AUTH),
    Mutant("tutorat_d_un_autre_eleve", "app/api/v1/tutorat/service.py",
           "    if t is None or t.eleve_hmac != eleve_hmac:", "    if t is None:", T_API),
    Mutant("idempotence_sans_empreinte", "app/api/v1/tutorat/service.py",
           "    if deja.empreinte != empreinte:", "    if False:", T_API),
    Mutant("version_non_verifiee", "app/api/v1/tutorat/service.py",
           "    if version != t.version:", "    if False:", T_API),
    Mutant("manifest_non_epingle_accepte", "app/curriculum/importers.py",
           '            raise ErreurImport("empreinte_manifest_non_epinglee")', "            pass", T_IMPORT),
    Mutant("document_source_non_verifie", "app/curriculum/integrite.py",
           "            if not s.fictive and s.sha256_document not in docs:", "            if False:", T_IMPORT),
    Mutant("generation_malgre_anomalie", "app/curriculum/integrite.py",
           "        if n.optionnelle or {n.id, n.chapitre_id, n.programme_id} & touches:",
           "        if n.optionnelle:", T_IMPORT),
    Mutant("lot_actif_altere_servi", "app/curriculum/depot.py",
           '            raise DepotInvalide(f"lot_actif_invalide:{etat[\'lot\']}")', "            pass", T_IMPORT),
    Mutant("corps_non_borne", "app/core/limites.py",
           "                if not valeur.isdigit() or int(valeur) > self.max_octets:",
           "                if False:", T_ATT),
]


def executer_suite(*cibles: str) -> int:
    """Code retour pytest : 0 vert, 1 au moins un test ÉCHOUE, autre = suite non exécutée."""
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-x", *(cibles or ("tests_cloud",)), "-p", "no:cacheprovider"],
        cwd=RACINE, capture_output=True, text=True,
    )
    return r.returncode


def main() -> int:
    # Revue session 2 (R2-12) : sans suite verte AVANT mutation, tout mutant paraissait
    # « tué » ; et un mutant qui casse l'import (erreur de collecte, code 2) était compté
    # tué alors qu'aucune assertion ne l'avait détecté.
    if executer_suite() != 0:
        print("BASELINE ROUGE : la suite échoue sans mutation, résultat non significatif")
        return 2
    survivants, inapplicables, non_executes = [], [], []
    for m in MUTANTS:
        f = RACINE / m.fichier
        original = f.read_text(encoding="utf-8")
        if original.count(m.avant) != 1:
            inapplicables.append(m.nom)
            print(f"INAPPLICABLE {m.nom}")
            continue
        try:
            f.write_text(original.replace(m.avant, m.apres), encoding="utf-8")
            code = executer_suite(*m.cibles)
        finally:
            f.write_text(original, encoding="utf-8")
        etiquette = {0: "SURVIVANT", 1: "TUÉ"}.get(code, f"NON_EXÉCUTÉ({code})")
        print(f"{etiquette:10} {m.nom}")
        if code == 0:
            survivants.append(m.nom)
        elif code != 1:
            non_executes.append(m.nom)
    tues = len(MUTANTS) - len(survivants) - len(inapplicables) - len(non_executes)
    print(f"\n{tues}/{len(MUTANTS)} mutants tués")
    return 1 if survivants or inapplicables or non_executes else 0


if __name__ == "__main__":
    sys.exit(main())
