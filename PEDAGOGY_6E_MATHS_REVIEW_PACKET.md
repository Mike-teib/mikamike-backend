# PEDAGOGY_6E_MATHS_REVIEW_PACKET

## But

Paquet de relecture humaine avant toute promotion de notion de mathématiques 6e vers `PROVEN_OFFICIAL`.

Source locale contrôlée :
- `pedagogy/sources_local/official/programme-mathematiques-cycle3-2025.pdf`
- taille : 527151 octets
- SHA-256 : `f3f79a75ca8be7f54409b8b7cee3eafd769c23d12e6c822a253454e2c703b508`
- source : programme de mathématiques du cycle 3, BO n°16 du 17 avril 2025, NOR MENE2504620A
- statut source : `RETRIEVED`
- `reference_verified=false` tant qu'un humain ne l'a pas confirmé.

Aucune notion n'est promue dans ce document.

## 1. Résultat de `sources_cli propose`

Le moteur de proposition cherche le titre candidat dans le texte extrait du PDF. Il a trouvé 11 candidats sur 23 :

| Notion candidate | Pages trouvées (PDF 1-based) | Interprétation |
|---|---|---|
| MATHS.6E.NC.nombres-entiers | 1, 5, 6, 7, 8, 9, 10, 12, 13, 14 | Titre générique fréquent ; choisir uniquement la section 6e avant promotion. |
| MATHS.6E.NC.nombres-decimaux | 1, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16 | Titre générique fréquent ; section 6e à isoler. |
| MATHS.6E.NC.division-euclidienne | 13, 14 | Correspondance forte avec les objectifs 6e. |
| MATHS.6E.NC.fractions | 1, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16 | Candidat trop large ; le programme 6e distingue plusieurs sous-thèmes. |
| MATHS.6E.NC.proportionnalite | 2, 4, 16, 18, 19, 26, 27 | Section 6e dédiée ; classement interne actuel à revoir. |
| MATHS.6E.NC.pourcentages | 16 | Correspondance forte, mais rattachement interne à revoir. |
| MATHS.6E.GM.perimetres | 17, 18, 19 | Correspondance forte dans Grandeurs et mesures. |
| MATHS.6E.GM.conversions-d-unites | 13, 19 | Présence réelle mais candidat très large. |
| MATHS.6E.GM.angles | 1, 17, 18, 20, 22, 23 | Présence réelle ; en 6e le programme rattache explicitement le travail sur les angles à la géométrie. |
| MATHS.6E.EG.cercle | 3, 19, 20, 21, 22, 23, 28 | Présence réelle ; privilégier la section 6e « Cercles et disques ». |
| MATHS.6E.EG.symetrie-axiale | 23 | Correspondance forte et localisée dans la section 6e. |

Une occurrence de titre n'est jamais suffisante pour une preuve. La promotion exige un extrait officiel exact, une page déclarée et le SHA-256 du document.

## 2. Candidats sans correspondance textuelle exacte du titre

| Candidat | État de revue | Action avant promotion |
|---|---|---|
| Repérage sur une demi-droite graduée | contenu explicitement présent | Le programme emploie des formulations « placer » / « repérer » ; garder ou renommer après choix d'un extrait exact. |
| Opérations sur les nombres décimaux | contenu explicitement présent | Granulariser addition/soustraction, multiplication et division. |
| Multiples et diviseurs | réactivation explicite | Présent comme acquis réactivé pour le calcul sur fractions ; décider s'il reste notion autonome ou prérequis. |
| Calcul mental et ordre de grandeur | partiellement explicite | Les ordres de grandeur sont explicites ; le calcul mental est surtout traité comme automatisme. |
| Longueur du cercle | intitulé à corriger | Préférer « Périmètre du disque ». |
| Aires | section explicite | Vérifier l'extraction et choisir des objectifs exacts. |
| Volume du pavé droit | trop spécifique | Remplacer par une notion générale sur cm³, comparaison et détermination de volumes. |
| Droites parallèles et perpendiculaires | surtout acquis antérieur | Traiter comme acquis/prérequis sauf décision pédagogique contraire. |
| Triangles et quadrilatères particuliers | mélange de niveaux | La 6e approfondit surtout les triangles ; scinder. |
| Solides usuels et patrons | surtout acquis antérieur | Resserrer vers la vision dans l'espace et les assemblages de cubes. |
| Tableaux et diagrammes | contenu présent sous autre structure | Ajouter enquête/collecte/filtrage et un candidat probabilités séparé. |
| Programmation de déplacements | contenu présent sous autre structure | Rattacher à « Initiation à la pensée informatique ». |

## 3. Manques prioritaires du registre 6e

- pensée algébrique / problèmes à nombre inconnu / motifs évolutifs ;
- probabilités ;
- médiatrice d'un segment ;
- bissectrice d'un angle ;
- somme des angles d'un triangle et cercle circonscrit ;
- calculs, problèmes et conversions sur horaires/durées ;
- planification d'enquête, collecte et filtrage de données ;
- vision dans l'espace à partir d'assemblages de cubes.

## 4. Ordre de décision recommandé

1. Confirmer humainement la référence de la source ; seulement alors passer `reference_verified=true`.
2. Corriger la structure du registre 6e : créer les manques et scinder/renommer les candidats trop larges ou mal classés.
3. Régénérer graphe, couverture et QA.
4. Relancer `sources_cli propose`.
5. Pour chaque candidat retenu, copier un extrait officiel exact depuis la bonne page et appeler `promote_notion`.
6. Une promotion documentaire laisse `review_status=NOT_REVIEWED`.
7. Un humain valide ensuite la notion (`APPROVED`) avant toute génération d'exercice ou de quiz.

## 5. Décision actuelle

**STOP volontaire au niveau de la promotion.** Le dépôt dispose maintenant du vrai PDF et de son SHA-256, mais la structure 6e doit être corrigée avant de transformer des candidats historiques en notions officielles.
