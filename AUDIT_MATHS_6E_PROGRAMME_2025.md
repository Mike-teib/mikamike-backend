# AUDIT_MATHS_6E_PROGRAMME_2025

## Objet

Audit contradictoire des 23 notions candidates de `pedagogy/data/notions/MATHS/6E.json` contre le programme officiel de mathématiques du cycle 3 publié au BO n°16 du 17 avril 2025 (NOR MENE2504620A), applicable à la 6e à la rentrée 2025-2026.

Cette revue ne constitue **pas** une preuve au sens du pipeline MikaMike : le PDF n'est pas encore enregistré localement avec SHA-256. Toutes les notions restent `UNPROVEN`, `NOT_REVIEWED`, `DRAFT`.

## Résultat synthétique

- 23 candidats examinés.
- 14 candidats sont globalement alignés avec un contenu explicitement présent en 6e, mais restent à granulariser ou à prouver verbatim.
- 7 candidats demandent un déplacement, renommage ou resserrement important.
- 2 candidats correspondent surtout à des acquis réactivés du cours moyen et ne doivent pas être traités comme nouvelles notions de 6e sans décision humaine.
- Plusieurs éléments explicites du programme 2025 manquent du registre actuel : algèbre / problèmes à nombre inconnu, probabilités, médiatrice, bissectrice, somme des angles d'un triangle et cercle circonscrit, horaires/durées, enquête statistique, vision dans l'espace par assemblages de cubes.

## Audit des 23 candidats

| Candidat actuel | Verdict audit | Page PDF indicative (1-based) | Action recommandée avant preuve |
|---|---|---:|---|
| Nombres entiers | ALIGNÉ-GROUPE | 13-14 | Conserver comme regroupement interne ; la source 6e traite ensemble nombres entiers et décimaux. |
| Nombres décimaux | ALIGNÉ | 13-14 | Conserver ; vérifier les objectifs exacts au moment de la promotion. |
| Repérage sur une demi-droite graduée | ALIGNÉ | 14 | Conserver ; objectif explicite pour les nombres décimaux et aussi pour les fractions. |
| Opérations sur les nombres décimaux | ALIGNÉ | 14 | Conserver mais distinguer addition/soustraction, multiplication et division si la banque exige une granularité fine. |
| Division euclidienne | ALIGNÉ | 14 | Conserver ; objectif explicite en 6e. |
| Multiples et diviseurs | RÉACTIVATION | 15 | La source les réactive pour le calcul sur les fractions ; ne pas en faire automatiquement une nouvelle notion autonome de 6e. |
| Calcul mental et ordre de grandeur | ALIGNÉ-PARTIEL | 13-14 | Ordres de grandeur explicites ; calcul mental relève surtout des automatismes. Séparer si nécessaire. |
| Fractions | TROP LARGE | 15-16 | Scinder au minimum : sens quotient, fraction opérateur, comparaison/encadrement, opérations, problèmes. |
| Proportionnalité | ALIGNÉ-MAIS-MAL-CLASSÉ | 27 | Déplacer hors de « Nombres et calculs » vers un domaine interne dédié à la proportionnalité. |
| Pourcentages | ALIGNÉ-MAIS-MAL-CLASSÉ | 16 | Rattacher au travail sur fractions/nombres, pas au chapitre interne « Proportionnalité » uniquement. |
| Périmètres | ALIGNÉ | 19 | Conserver ; inclure les figures composées. |
| Longueur du cercle | À RENOMMER | 19 | Préférer « Périmètre du disque » ; le programme tolère « périmètre du cercle » mais présente le disque comme référence. |
| Aires | ALIGNÉ | 19 | Conserver ; inclure conversions d'aires et formules carré/rectangle. |
| Volume du pavé droit | TROP SPÉCIFIQUE | 19 | Remplacer par une notion plus générale sur cm³, comparaison et détermination de volumes ; aucune formule de volume du pavé n'est à supposer sans preuve. |
| Conversions d'unités | ALIGNÉ-MAIS-LARGE | 19-20 | Distinguer longueurs, aires et durées si nécessaire. |
| Angles | ALIGNÉ-MAIS-MAL-CLASSÉ | 23 | Déplacer de « Grandeurs et mesures » vers géométrie ; le programme 6e intègre explicitement mesure et objet géométrique. |
| Droites parallèles et perpendiculaires | RÉACTIVATION | 20-21 | Le programme les installe au cours moyen ; en 6e, les considérer comme acquis/prérequis sauf décision pédagogique contraire. |
| Cercle | ALIGNÉ | 23 | Renommer éventuellement « Cercles et disques » ; le programme 6e ajoute définitions et problèmes de distance. |
| Triangles et quadrilatères particuliers | À SCINDER | 23 | En 6e, le programme développe surtout les triangles ; les quadrilatères sont largement réactivés du cours moyen. Créer une notion dédiée triangles. |
| Symétrie axiale | ALIGNÉ | 23 | Conserver ; objectifs explicites. |
| Solides usuels et patrons | À RESSERRER | 23-24 | Les patrons/solides usuels sont surtout acquis du CM2 ; la nouveauté 6e porte sur la vision dans l'espace et les assemblages de cubes. |
| Tableaux et diagrammes | ALIGNÉ-PARTIEL | 25-26 | Renommer le domaine en « Organisation et gestion de données et probabilités » et ajouter enquête/collecte/filtrage. |
| Programmation de déplacements | ALIGNÉ-MAIS-MAL-CLASSÉ | 28 | Rattacher à « Initiation à la pensée informatique » ; couvrir instructions, séquences, répétitions et chemin simple. |

## Manques prioritaires du registre 6e

1. **Algèbre / pensée pré-algébrique** : résolution de problèmes avec nombre inconnu et motifs évolutifs.
2. **Probabilités** : probabilité entre 0 et 1, calcul en équiprobabilité, comparaison fréquence/probabilité.
3. **Médiatrice d'un segment**.
4. **Bissectrice d'un angle**.
5. **Triangles** : construction, propriétés angulaires, somme des angles, médiatrices concourantes et cercle circonscrit.
6. **Horaires et durées** : calculs, problèmes et conversions.
7. **Enquête statistique** : planifier, recueillir, consigner et filtrer des données.
8. **Vision dans l'espace** : assemblages de cubes.

## Décision de sécurité

Aucune suppression, renommage d'identifiant, promotion `PROVEN_OFFICIAL` ou passage `APPROVED` n'est réalisé dans cet audit. Les changements de structure doivent être appliqués dans un commit séparé avec migration des prérequis et régénération du graphe.

## Prochaine étape technique

1. Enregistrer le PDF officiel dans `pedagogy/sources_local/official/`.
2. Calculer et enregistrer son SHA-256 via `sources_cli register`.
3. Régénérer les candidats 6e sur la structure 2025 ci-dessus.
4. Lancer `sources_cli propose`.
5. Promouvoir uniquement les libellés vérifiés page par page ; garder `review_status=NOT_REVIEWED`.
6. Faire approuver humainement les notions avant toute génération d'exercice ou de quiz.
