# EMAIL_PROVIDER_SETUP — fournisseur de courriel (session cloud 5)

**État : aucun courriel réel n'a été envoyé ; aucune clé n'est présente dans le dépôt.** Le code est
prêt pour un relais SMTP transactionnel quelconque ; le choix du prestataire et la création du
compte restent à faire par Mike (hors dépôt).

## 1. Abstraction

| nom (code) | alias anglais | usage |
|---|---|---|
| `TransportCourriel` (Protocol : `envoyer(Message) -> None`) | `EmailProvider` | interface unique |
| `TransportFaux` | `FakeEmailProvider` | tests, CI, dev (mémoire bornée à 1000 messages) |
| `TransportJournal` | — | n'envoie rien, journalise une empreinte du destinataire |
| `TransportSMTP` | `SMTPEmailProvider` | fournisseur réel générique (tout relais SMTP) |

Sélection : `MIKA_EMAIL_TRANSPORT` = `faux` (défaut hors production) | `journal` | `smtp` | nom d'un
fournisseur enregistré par `courriel.enregistrer_transport(nom, fabrique)` (API HTTP d'un prestataire,
à écrire le jour venu sans toucher au reste du code).

En production (`MIKA_ENV=production`) : `faux` et `journal` sont refusés ; `smtp` exige un canal
chiffré et des identifiants ; toute configuration incomplète **fait refuser le démarrage** (aucune
connexion n'est tentée au démarrage : la validation est purement locale).

## 2. Variables d'environnement (valeurs dans le coffre du déploiement, jamais dans git)

| variable | obligatoire | défaut | contrôle |
|---|---|---|---|
| `MIKA_EMAIL_TRANSPORT` | oui en production | `faux` hors production | `smtp` en staging/production |
| `MIKA_SMTP_HOST` | oui | — | non vide |
| `MIKA_SMTP_PORT` | non | 587 (`starttls`), 465 (`ssl`), 25 (`aucune`) | 1..65535 |
| `MIKA_SMTP_SECURITE` | non | `starttls` | `starttls` / `ssl` / `aucune` (`aucune` interdit en production) |
| `MIKA_SMTP_FROM` | oui | — | adresse, sans retour à la ligne |
| `MIKA_SMTP_FROM_NAME` | non | `MikaMike` | sans retour à la ligne |
| `MIKA_SMTP_USER` | oui en production | — | va avec le mot de passe |
| `MIKA_SMTP_PASSWORD` | oui en production | — | **secret** ; jamais journalisé ni affiché (`repr` masqué) |
| `MIKA_SMTP_DELAI_S` | non | 10 | 1..60 secondes |

## 3. Garanties

- TLS vérifié : `ssl.create_default_context()` (certificat et nom d'hôte) pour `starttls` et `ssl` ;
- identifiants refusés sur une connexion non chiffrée, même hors production ;
- injection d'en-têtes impossible : retour chariot / saut de ligne refusés dans destinataire, sujet,
  type, expéditeur ;
- journaux : `courriel_envoye type=…` ou `courriel_echec type=… erreur=<classe>` ; jamais l'adresse,
  le corps (qui contient le code de vérification) ni les identifiants ;
- panne du fournisseur : l'inscription réussit quand même (201, compte créé, adresse non vérifiée) ;
  le renvoi `POST /comptes/verification-email` répond **503 `courriel_indisponible`** ; le front
  propose de réessayer plus tard (quota de renvoi inchangé) ;
- en-têtes `Message-ID` unique, `Auto-Submitted: auto-generated`, `X-MikaMike-Type`.

## 4. Mise en service (staging d'abord)

1. Choisir un prestataire avec relais SMTP authentifié et **hébergement UE** (données de parents) ;
   signer le DPA (sous-traitant RGPD) — décision Mike / DPO.
2. Domaine d'expédition : SPF, DKIM, DMARC publiés pour le domaine de `MIKA_SMTP_FROM`.
3. Créer des identifiants **dédiés au staging** (jamais ceux de la production), les ranger dans le
   coffre du déploiement.
4. Poser les variables du §2 dans l'environnement staging, avec `MIKA_EMAIL_TRANSPORT=smtp`.
5. Démarrer : un refus de démarrage nomme la variable fautive (jamais sa valeur).
6. Smoke : inscription avec une boîte de test contrôlée par l'équipe ⇒ courriel reçu, code valide ;
   vérifier dans les journaux la présence de `courriel_envoye` et l'absence de l'adresse.
7. Production : mêmes étapes avec des identifiants distincts, après validation staging.

## 5. Tests (aucun réseau externe)

`tests_cloud/test_email_provider.py` : configuration (22 cas), échange SMTP complet contre un serveur
local éphémère, connexion refusée sans fuite, ordre `starttls → login → envoi` avec contexte TLS
vérifié, panne ⇒ inscription 201 / renvoi 503. Mutants : `smtp_*` dans `tools/mutation_check.py`.
