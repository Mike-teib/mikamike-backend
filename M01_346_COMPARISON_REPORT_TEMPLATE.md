# M01 — Rapport de non-régression (Maths Cycle 3)

> Gabarit rempli par `M01_346_COMPARISON_TOOL.py`. Tant que les deux corpus ne sont pas
> fournis, **aucune comparaison n'a été faite** : ce fichier reste un gabarit.
> L'outil est en lecture seule : la publication M01 n'est jamais modifiée.

- Statut : **{{STATUT_COMPARAISON}}**
- Corpus publié (ancienne publication M01) : `{{CORPUS_PUBLIE}}`
- Corpus officiel ré-extrait : `{{CORPUS_REEXTRAIT}}`
- Effectif attendu : {{EFFECTIF_ATTENDU}} · publié : {{EFFECTIF_PUBLIE}} · ré-extrait : {{EFFECTIF_REEXTRAIT}}

## Avertissements
{{AVERTISSEMENTS}}

## Répartition par statut principal

| Statut | Nombre |
|---|---|
{{TABLEAU_COMPTES}}

Définitions :
- **IDENTIQUE** : texte, formules, source et affectation identiques.
- **TEXTE_MODIFIE** : texte différent hors formules.
- **FORMULE_MODIFIEE** : contenu mathématique différent (nombres, opérateurs, variables).
- **NOTATION_DEGRADEE** : même mathématique, notation appauvrie (10⁻³→10-3, 1/10→0,1, x²→x2, √ ou symbole perdu, LaTeX cassé).
- **SOURCE_DIFFERENTE** : source, page ou version différente.
- **NOTION_REAFFECTEE** : même texte, niveau / domaine / chapitre différent.
- **NOTION_ABSENTE** : aucune notion ré-extraite correspondante.

## Écarts (toutes les notions non identiques)

| Notion publiée | Notion ré-extraite | Statut | Drapeaux | Détail notation |
|---|---|---|---|---|
{{TABLEAU_ECARTS}}

## Notions présentes uniquement dans la ré-extraction
{{NOUVELLES}}

## Décisions à prendre (humain)
Aucune correction n'est appliquée automatiquement à la publication. Pour chaque écart :
corriger la publication, conserver l'ancienne formulation (avec justification), ou marquer
la notion DEPRECATED — décision tracée dans le registre.
