# Sources officielles locales

Déposer ici (`official/`) les PDF officiels (BO, Éduscol) téléchargés manuellement,
puis renseigner `local_path` dans `pedagogy/data/sources/official_sources.json`.
L'empreinte SHA-256 est recalculée par `python -m pedagogy.sources_cli register`.
Aucun fichier n'est téléchargé automatiquement (réseau non requis).
