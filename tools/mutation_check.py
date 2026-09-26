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

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, NamedTuple, Tuple

RACINE = Path(__file__).resolve().parent.parent


class Mutant(NamedTuple):
    nom: str
    fichier: str
    avant: str
    apres: str
    # Suite(s) exécutée(s) pour ce mutant (défaut : tests_cloud hors fichiers LENTS — perf et
    # migrations en sous-processus — qui ne couvrent aucun mutant par défaut ; ils ont leurs
    # propres mutants ciblés. Sans cela le job CI dépassait son délai, session 3).
    cibles: Tuple[str, ...] = ("tests_cloud", "--ignore=tests_cloud/test_import_perf.py",
                               "--ignore=tests_cloud/test_migrations.py",
                               "--ignore=tests_cloud/test_migrations_validation.py")


T_AUTH = ("tests_cloud/test_auth.py", "tests_cloud/test_review_session1.py")
T_API = ("tests_cloud/test_mika_api.py",)
T_IMPORT = ("tests_cloud/test_import_v2_integrite.py", "tests_cloud/test_review_session1.py")
T_ATT = ("tests_cloud/test_attaques.py", "tests_cloud/test_review_session1.py")
T_S3 = ("tests_cloud/test_review_session2.py",)
T_RL = ("tests_cloud/test_limitation.py",)
T_EQ = ("tests_cloud/test_equivalence.py",)
T_MIG = ("tests_cloud/test_migrations_validation.py",)
T_API2 = ("tests_cloud/test_mika_api_audit.py",)
T_HARN = ("tests_cloud/test_import_harnais.py",)
T_SEC = ("tests_cloud/test_securite_s3.py",)
T_R19 = ("tests_cloud/test_verification_email.py", "tests_cloud/test_e2e_parent_enfant.py")
T_OBS = ("tests_cloud/test_observabilite.py",)
T_PUB = ("tests_cloud/test_publication.py",)
T_RAP = ("tests_cloud/test_rapport_import.py",)
T_CHAP = ("tests_cloud/test_chapitrage.py", "tests_cloud/test_import_harnais.py", "tests_cloud/test_publication.py",
          "tests_cloud/test_text_quality_s4.py")
T_REC = ("tests_cloud/test_recurrence_s4.py", "tests_cloud/test_pedagogie_mika.py")
T_MATH = ("tests_cloud/test_maths_etendu.py",)
T_DEC = ("tests_cloud/test_invitations.py", "tests_cloud/test_equivalence.py", "tests_cloud/test_securite_s3.py",
         "tests_cloud/test_e2e_parent_enfant.py")


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
           'niveau = "ACQUIS_ASSISTE" if etat.avec_aide else "ACQUIS_AUTONOME"',
           'niveau = "ACQUIS_AUTONOME"'),
    Mutant("solution_donnee_immediatement", "app/curriculum/pedagogie/tuteur.py",
           "if etat.questions_posees < len(self.plan.questions_intermediaires):",
           "if False:\n            pass\n        if True:\n            return self._emettre(etat, Action.CORRECTION_COMMENTEE, self.plan.correction_commentee)\n        if False:"),
    Mutant("idor_session", "app/api/v1/session/session_manager.py",
           "    if session_obj.eleve_hmac != eleve_hmac:", "    if False:"),
    Mutant("rgpd_effacement_incomplet", "app/api/v1/rgpd/router.py",
           "TABLES_ELEVE = (TentativeExercice, EtatCompetence, TacheRappelMemoire, MikaSessionState,\n"
           "                TutoratSession, TutoratRequete)",
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
           '        if (c.get("typ") != TYP_ELEVE or c.get("role") != "eleve" or not isinstance(c.get("sub"), str)\n',
           '        if (not isinstance(c.get("sub"), str)\n', T_AUTH),
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
    # ---------------------------------------------------------------- session 3
    Mutant("jeton_eleve_lien_non_reverifie", "app/core/auth.py",
           "        if liens.relation(db, emetteur.id, hmac_eleve(pseudo_id)) != emetteur.role:",
           "        if False:", T_S3),
    Mutant("jeton_eleve_compte_desactive", "app/core/auth.py",
           "        if emetteur is None or not emetteur.actif or", "        if emetteur is None or", T_S3),
    Mutant("url_alembic_non_echappee", "app/db/migrations.py",
           'url.replace("%", "%%")', "url", T_S3),
    Mutant("ddl_sqlite_non_transactionnel", "app/db/migrations.py",
           '    if engine.dialect.name != "sqlite":\n        return', "    return", T_S3),
    Mutant("double_soumission_409", "app/api/v1/tutorat/service.py",
           "        if rejeu is not None:\n            return rejeu\n        raise _err(status.HTTP_409_CONFLICT, \"version_perimee\")",
           "        raise _err(status.HTTP_409_CONFLICT, \"version_perimee\")", T_S3),
    Mutant("etat_corrompu_accepte", "app/api/v1/tutorat/service.py",
           "        if not all(_type_valide(k, v) for k, v in d.items()):", "        if False:", T_S3),
    Mutant("comprehension_ratee_comptee_reussie", "app/api/v1/tutorat/service.py",
           "    return etat.resolu and etat.comprehension_verifiee is not False", "    return etat.resolu", T_S3),
    Mutant("connexion_sans_leurre", "paiement_comptes/crud_billing.py",
           "compte.mot_de_passe_hash if compte else _hash_leurre()", "compte.mot_de_passe_hash if compte else 'x'",
           T_S3),
    Mutant("export_rgpd_sans_journal", "app/api/v1/rgpd/router.py",
           '        "requetes_tutorat_mika": export_requetes,\n', "", T_S3),
    Mutant("identifiant_64_elargi", "app/core/validation.py",
           "Identifiant64 = Annotated[str, Field(min_length=1, max_length=64,",
           "Identifiant64 = Annotated[str, Field(min_length=1, max_length=128,", T_S3),
    Mutant("connexion_non_limitee", "paiement_comptes/router_comptes.py",
           "    paires = limitation.cles_connexion(request, data.email)\n    limitation.exiger(*paires)\n",
           "    paires = limitation.cles_connexion(request, data.email)\n", T_RL),
    Mutant("connexion_bloquee_par_email_seul", "app/core/limitation.py",
           "    if email_global_actif():", "    if True:", T_RL),
    Mutant("backoff_constant", "app/core/limitation.py",
           "self.backoff_base_s * (2 ** (n - self.max_echecs))", "self.backoff_base_s", T_RL),
    Mutant("pas_de_reset_sur_succes", "app/core/limitation.py",
           "                lim.succes(cle)", "                pass", T_RL),
    Mutant("x_forwarded_for_cru", "app/core/limitation.py",
           "    if hops > 0:", "    if True:", T_RL),
    Mutant("jetons_invalides_non_comptes", "app/core/auth.py",
           "    except HTTPException:\n        limitation.jeton_invalide(request)\n        raise",
           "    except HTTPException:\n        raise", T_RL),
    Mutant("historique_oublie_pendant_blocage", "app/core/limitation.py",
           "max(e.echecs[-1], e.bloque_jusqua) <= maintenant", "e.echecs[0] <= maintenant", T_RL),
    Mutant("equivalence_ambigu_accepte", "app/curriculum/equivalence.py",
           "    if sym == Verdict.NEEDS_HUMAN_REVIEW or sym == Verdict.AMBIGUOUS:", "    if False:", T_EQ),
    Mutant("equivalence_forme_ignoree", "app/curriculum/equivalence.py",
           "    if not ok:\n", "    if False:\n", T_EQ),
    Mutant("equivalence_autre_variable", "app/curriculum/equivalence.py",
           "    if vars_att and vars_rep - vars_att:", "    if False:", T_EQ),
    Mutant("equivalence_conversion_auto", "app/curriculum/equivalence.py",
           "    if ua != ur:", "    if False:", T_EQ),
    Mutant("migration_non_atomique_validation", "app/db/migrations.py",
           '    if engine.dialect.name != "sqlite":\n        return', "    return", T_MIG),
    Mutant("cli_db_trace_sur_erreur", "tools/db.py",
           "    except (CommandError, m.SchemaNonAJour, ValueError, KeyError) as exc:",
           "    except ZeroDivisionError as exc:", T_MIG),
    Mutant("tutorat_termine_modifiable", "app/api/v1/tutorat/service.py",
           '    if etat.termine:\n        raise _err(status.HTTP_409_CONFLICT, "tutorat_termine")',
           '    if False:\n        raise _err(status.HTTP_409_CONFLICT, "tutorat_termine")', T_API2),
    Mutant("prerequis_assiste_suffit", "app/curriculum/pedagogie/tuteur.py",
           'ETATS_PREREQUIS_SOLIDES = frozenset({"ACQUIS_AUTONOME", "MAITRISE"})',
           'ETATS_PREREQUIS_SOLIDES = frozenset({"ACQUIS_AUTONOME", "MAITRISE", "ACQUIS_ASSISTE"})', T_API2),
    Mutant("vue_publique_fuit_les_erreurs", "app/api/v1/tutorat/service.py",
           '            "messages": list(etat.messages),',
           '            "messages": list(etat.messages), "erreurs": list(etat.erreurs),', T_API2),
    Mutant("aide_future_divulguee", "app/curriculum/pedagogie/tuteur.py",
           '                                 Action.DONNER_INDICE, f"Indice : {ind} Réessaie.")',
           '                                 Action.DONNER_INDICE, f"Indice : {ind} Réessaie. " + " ".join(self.ex.indices))',
           T_API2),
    Mutant("source_fictive_publiable", "app/curriculum/integrite.py",
           "            if s.fictive:\n", "            if False:\n", T_HARN),
    Mutant("republication_non_idempotente", "app/curriculum/depot.py",
           '            if precedent and precedent["lot"] == lot:\n                raise DepotInvalide',
           '            if False:\n                raise DepotInvalide', T_HARN),
    Mutant("reprise_sans_revalidation", "app/curriculum/depot.py",
           "            if self._importer(cible, sha256_manifest).statut != \"VALIDATED\":\n"
           "                raise DepotInvalide(f\"copie_existante_invalide:{lot}\")",
           "            pass", T_HARN),
    Mutant("historique_non_borne", "app/curriculum/depot.py",
           '"precedent": _borner(precedent)}', '"precedent": precedent}', T_HARN),
    Mutant("import_partiel_accepte", "app/curriculum/importers.py",
           '    if any(f["etat"] == "FAILED" for f in res.fichiers.values()):\n        res.statut = "FAILED"\n        return res',
           "    pass", T_HARN),
    Mutant("sub_eleve_non_valide", "app/core/auth.py",
           '                or not re.fullmatch(ID_PATTERN, c["sub"])\n', "", T_SEC),
    Mutant("jeton_geant_decode", "app/core/auth.py",
           ' or len(jeton) > 4096:', ':', T_SEC),
    # ---------------------------------------------------------------- décisions D5 / D8 / D15
    Mutant("d8_role_ignore", "paiement_comptes/liens.py",
           " or compte.role != inv.relation:", ":", T_DEC),
    Mutant("d8_sans_expiration", "paiement_comptes/liens.py",
           "expire_le=now + _dt.timedelta(minutes=ttl_invitation_min())",
           "expire_le=now + _dt.timedelta(days=3650)", T_DEC),
    Mutant("d8_code_devinable", "paiement_comptes/liens.py",
           "_secrets.token_bytes(15)", "bytes(15)", T_DEC),
    Mutant("d8_confirmation_facultative", "app/api/v1/liens/router.py",
           "        if v is not True:", "        if False:", T_DEC),
    Mutant("d8_emission_sans_lien", "app/api/v1/liens/router.py",
           "    auth.autoriser(qui, data.student_pseudo_id,", "    (lambda *a: None)(qui, data.student_pseudo_id,", T_DEC),
    Mutant("d8_force_brute_non_comptee", "app/api/v1/liens/router.py",
           "        limitation.enregistrer(paires, reussi=False)\n", "", T_DEC),
    Mutant("d5_ambigu_accepte", "app/api/v1/mikamike/catalogue.py",
           "    return ligne.decision == Decision.ACCEPTER", "    return ligne.decision != Decision.REFUSER", T_DEC),
    Mutant("d15_session_id_previsible", "app/api/v1/session/session_manager.py",
           '"s" + secrets.token_hex(24)', '"s" + "0" * 48', T_DEC),
    # ---------------------------------------------------------------- session 4 : R19 / révocation
    Mutant("r19_acceptation_sans_verification", "paiement_comptes/liens.py",
           "    if verification_ok_pour_invitation(compte):", "    if False:", T_R19),
    Mutant("r19_jeton_non_lie_a_l_adresse", "paiement_comptes/verification_email.py",
           " or compte.email != v.email_cible:", ":", T_R19),
    Mutant("r19_sans_expiration", "paiement_comptes/verification_email.py",
           "expire_le=now + _dt.timedelta(minutes=ttl_min())", "expire_le=now + _dt.timedelta(days=3650)", T_R19),
    Mutant("revocation_compte_ignoree_moi", "paiement_comptes/router_comptes.py",
           "    if isinstance(ver, bool) or not isinstance(ver, int) or ver != (compte.jeton_version or 0):",
           "    if False:", T_R19),
    Mutant("revocation_compte_ignoree_garde", "app/core/auth.py",
           "    if (compte.jeton_version or 0) != qui.version:", "    if False:", T_R19),
    Mutant("revocation_eleve_ignoree", "app/core/auth.py",
           " or (emetteur.jeton_version or 0) != qui.version:", ":", T_R19),
    Mutant("mot_de_passe_sans_revocation", "paiement_comptes/router_comptes.py",
           "    _revoquer(compte)  # un jeton volé", "    pass  # un jeton volé", T_R19),
    Mutant("suppression_sans_mot_de_passe", "paiement_comptes/router_comptes.py",
           "    _exiger_mot_de_passe(request, compte, data.mot_de_passe)\n    ab = compte.abonnement",
           "    ab = compte.abonnement", T_R19),
    Mutant("journal_chemin_brut", "app/core/observabilite.py",
           '            route = getattr(scope.get("route"), "path", None) or "(non_routee)"',
           '            route = scope.get("path") or "(non_routee)"', T_OBS),
    Mutant("journal_request_id_non_filtre", "app/core/observabilite.py",
           "rid = entrant if _RID.fullmatch(entrant) else uuid.uuid4().hex", "rid = entrant or uuid.uuid4().hex", T_OBS),
    Mutant("journal_message_d_exception", "app/core/observabilite.py",
           "            exception = type(exc).__name__", "            exception = str(exc)", T_OBS),
    Mutant("publication_chapitre_ambigu", "app/curriculum/publication.py",
           "    if chap is None or chap.ambigu or chap.programme_id != n.programme_id:", "    if chap is None:", T_PUB),
    Mutant("publication_sans_empreinte", "app/curriculum/publication.py",
           "        elif publies.get(contenu.id) == emp:", "        elif contenu.id in publies:", T_PUB),
    Mutant("publication_contenu_non_pret", "app/curriculum/publication.py",
           "        if ev.etat != EtatPublication.READY_FOR_PUBLICATION:", "        if False:", T_PUB),
    Mutant("publication_source_fictive", "app/curriculum/publication.py",
           "(source.fictive and not autoriser_fictif) or (", "(", T_PUB),
    Mutant("rapport_quarantaine_incomplete", "app/curriculum/rapport_import.py",
           "if st != StatutPreuve.PROVEN.value or nid in touches", "if nid in touches", T_RAP),
    Mutant("rapport_import_repete_non_signale", "app/curriculum/rapport_import.py",
           '            if rapport["comparaison"]["identique_au_lot_actif"]:', "            if False:", T_RAP),
    Mutant("import_publie_sans_confirmation", "tools/import_lot.py",
           "    if not a.depot or not a.confirmer:", "    if not a.depot:", T_RAP),
    Mutant("s4_01_generables_ignorent_import", "app/curriculum/importers.py",
           "    res.integrite = res.integrite._replace(generables=frozenset(res.integrite.generables - touchees))\n", "",
           T_CHAP),
    Mutant("chapitrage_lexical_accepte", "app/curriculum/chapitrage.py",
           '    if p.type == "proximite_lexicale":\n        return None, "preuve_lexicale_insuffisante"\n', "", T_CHAP),
    Mutant("chapitrage_annexe_acceptee", "app/curriculum/chapitrage.py",
           "    if any(a.page_debut <= p.page <= a.page_fin for a in s.annexes):", "    if False:", T_CHAP),
    Mutant("chapitrage_titre_de_colonne", "app/curriculum/chapitrage.py",
           "        if p.cellule.ligne == 0:", "        if False:", T_CHAP),
    Mutant("chapitrage_colonnes_ignorees", "app/curriculum/chapitrage.py",
           "    if avec_colonnes:", "    if False:", T_CHAP),
    Mutant("publication_rattachement_declare", "app/curriculum/publication.py",
           '    elif res.rattachements.get(n.id) != "PROUVE":', "    elif False:", T_CHAP),
    Mutant("texte_titre_absorbe_ignore", "app/curriculum/text_quality.py",
           "    if _titre_absorbe(t):", "    if False:", T_CHAP),
    Mutant("texte_unicode_anormal_ignore", "app/curriculum/text_quality.py",
           "    if _unicode_anormal(brut):", "    if False:", T_CHAP),
    Mutant("recurrence_implication_inversee", "app/curriculum/pedagogie/recurrence.py",
           '            out.append("HER_IMPLICATION_INVERSEE")', "            pass", T_REC),
    Mutant("recurrence_hypothese_sans_rang", "app/curriculum/pedagogie/recurrence.py",
           '        out.append("HYP_SANS_RANG")', "        pass", T_REC),
    Mutant("recurrence_etape_hors_ordre", "app/curriculum/pedagogie/recurrence.py",
           "    conf = sorted(conf, key=lambda c: ordre[ETAPE_DE[c]])", "    conf = sorted(conf)", T_REC),
    Mutant("recurrence_fonction_auxiliaire_acceptee", "app/curriculum/pedagogie/recurrence.py",
           "    if diff == 0:\n        return valide", "    if True:\n        return valide", T_REC),
    Mutant("limite_unilaterale", "app/curriculum/verifiers/maths_etendu.py",
           'sympy.limit(f, _X, p, dir="+-")', "sympy.limit(f, _X, p)", T_MATH),
    Mutant("arrondi_nombre_de_decimales_ignore", "app/curriculum/verifiers/maths_etendu.py",
           "    if nb != decimales:", "    if False:", T_MATH),
    Mutant("probabilite_hors_intervalle", "app/curriculum/verifiers/maths_etendu.py",
           "    if not (0 <= v <= 1):", "    if False:", T_MATH),
    Mutant("ensemble_bornes_fermees", "app/curriculum/verifiers/maths_etendu.py",
           'left_open=(g == "]" or va == -sympy.oo)', "left_open=False", T_MATH),
    Mutant("angle_unite_ignoree", "app/curriculum/verifiers/maths_etendu.py",
           'return valide("angle_egal") if ur == unite else revue', 'return valide("angle_egal") if True else revue', T_MATH),
    Mutant("d15_creation_implicite_en_enforce", "app/api/v1/session/router.py",
           "    if g.qui is not None:\n        GestionnaireSession.exiger_existante",
           "    if False:\n        GestionnaireSession.exiger_existante", T_DEC),
]


IGNORES = shutil.ignore_patterns(".git", ".venv", "venv", "__pycache__", "*.db", "reports", "checkpoints")


_RACINE_EXEC: List[Path] = []  # copie jetable en cours de mutation (vide : dépôt réel)


def executer_suite(*cibles: str) -> int:
    """Code retour pytest : 0 vert, 1 au moins un test ÉCHOUE, autre = suite non exécutée."""
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-x", *(cibles or ("tests_cloud",)), "-p", "no:cacheprovider"],
        cwd=_RACINE_EXEC[0] if _RACINE_EXEC else RACINE, capture_output=True, text=True,
    )
    return r.returncode


def main(argv=None) -> int:
    """`--seulement a,b` : ne rejoue que ces mutants (vérification ciblée d'un correctif)."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["--seulement"] and len(argv) == 2:
        noms = set(argv[1].split(","))
        inconnus = noms - {m.nom for m in MUTANTS}
        if inconnus:
            print(f"mutants inconnus : {sorted(inconnus)}")
            return 2
        MUTANTS[:] = [m for m in MUTANTS if m.nom in noms]
    # Revue session 2 (R2-12) : sans suite verte AVANT mutation, tout mutant paraissait
    # « tué » ; et un mutant qui casse l'import (erreur de collecte, code 2) était compté
    # tué alors qu'aucune assertion ne l'avait détecté.
    if executer_suite() != 0:
        print("BASELINE ROUGE : la suite échoue sans mutation, résultat non significatif")
        return 2
    survivants, inapplicables, non_executes = [], [], []
    # Revue session 3 (S3-11) : les mutants étaient écrits dans l'ARBRE DE TRAVAIL ; un arrêt
    # brutal (SIGKILL, timeout CI) y laissait un bug injecté, et un pytest lancé en parallèle
    # testait du code muté. On mute désormais une COPIE jetable du dépôt.
    with tempfile.TemporaryDirectory(prefix="mutation-") as tmp:
        copie = Path(tmp) / "depot"
        shutil.copytree(RACINE, copie, ignore=IGNORES)
        _RACINE_EXEC[:] = [copie]
        try:
            return _muter(copie, survivants, inapplicables, non_executes)
        finally:
            _RACINE_EXEC.clear()


def _muter(copie: Path, survivants, inapplicables, non_executes) -> int:
    for m in MUTANTS:
        f = copie / m.fichier
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
