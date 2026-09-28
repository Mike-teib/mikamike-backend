# MikaMike — checklist Google Play / Apple App Store

État vérifié au 28 septembre 2026.

## Fondations déjà validées

- PWA installable sur PC / mobile / tablette.
- Conteneur Capacitor Android + iOS.
- Micro web + micro natif Android/iOS.
- Auth élève réelle conservée.
- Tuteur réel branché.
- Android debug APK compilé en CI.
- iOS simulateur compilé en CI avec Xcode 26.6 / SDK iOS 26.5.
- Bundle ID natif : `fr.mikamike.app`.

## Google Play — exigence actuelle

Depuis le 31 août 2026, une nouvelle application ou mise à jour mobile doit cibler Android 16 / API 36 ou supérieur.

Le socle Capacitor 8 utilisé par MikaMike est aligné sur `targetSdkVersion 36`.

Avant soumission :
- produire un **Android App Bundle (.aab)** release, pas l'APK debug ;
- créer/conserver la clé de signature hors Git ;
- configurer Play App Signing ;
- remplir fiche Store, classification, Data Safety et informations de confidentialité ;
- tester d'abord sur la piste Internal testing.

## Apple App Store — exigence actuelle

Depuis le 28 avril 2026, les apps envoyées à App Store Connect doivent être construites avec Xcode 26 ou ultérieur et un SDK iOS/iPadOS 26 ou ultérieur.

La CI MikaMike a déjà validé une compilation simulateur avec Xcode 26.6 et le SDK iOS 26.5.

Avant soumission :
- générer une Archive iOS release signée ;
- configurer Apple Developer / App Store Connect ;
- créer les certificats et profils de provisioning hors Git ;
- vérifier les permissions `NSMicrophoneUsageDescription` et `NSSpeechRecognitionUsageDescription` ;
- compléter confidentialité, collecte de données, classification d'âge et métadonnées Store ;
- tester d'abord via TestFlight sur iPhone et iPad physiques.

## Enfants / mineurs

MikaMike s'adresse à des élèves, donc la revue Store doit traiter explicitement :
- minimisation des données ;
- finalité pédagogique ;
- politique de confidentialité accessible ;
- consentement / information parentale selon le parcours retenu ;
- absence de publicité comportementale destinée aux mineurs ;
- permissions micro déclenchées uniquement par une action de l'élève.

## Assets à finaliser avant release publique

Les icônes techniques actuelles servent aux builds et à la PWA. Avant publication :
- icône Store définitive ;
- splash screens définitifs ;
- captures téléphone + tablette ;
- texte court/long des fiches Store ;
- URL support et politique de confidentialité.

## Porte de release

Ne jamais stocker clés Android, certificats Apple, mots de passe ou profils de signature dans Git.

La publication Store reste une action externe distincte de la compilation technique et doit utiliser les comptes développeur autorisés.
