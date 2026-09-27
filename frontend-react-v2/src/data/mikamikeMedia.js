/**
 * Registre Officiel des Illustrations MikaMike (WordPress mikamike.fr)
 * Contient les illustrations validées du 27/09/2026 et de la médiathèque complète.
 * 
 * Charte graphique :
 * - ZÉRO VIOLET (Doctrine absolue)
 * - Palette MikaMike : Vert (#10b981 / #059669), Turquoise (#06b6d4 / #0284c7), Bleu (#2563eb / #3b82f6), Orange (#f97316), Blanc (#ffffff)
 */

export const MIKAMIKE_MEDIA = {
  // --- 1. NOUVELLES ILLUSTRATIONS 3D 27/09/2026 (IDs 588 - 594) ---
  LANDING_HERO: {
    id: 594,
    date: '2026-09-27',
    remoteUrl: 'https://mikamike.fr/wp-content/uploads/2026/09/Image-ChatGPT-27-sept.-2026-13_45_03-1.png',
    localUrl: '/assets/illustrations/594_Image-ChatGPT-27-sept.-2026-13_45_03-1.png',
    title: 'Interface globale MikaMike - Accueil & Vue d\'ensemble',
    alt: 'Mika le chat mascotte devant un ordinateur portable entouré d\'élèves souriants et d\'éléments de la plateforme MikaMike',
    aspectRatio: '16/9',
    useCases: ['accueil_eleve', 'hero_main', 'landing']
  },
  METHOD_HERO: {
    id: 593,
    date: '2026-09-27',
    remoteUrl: 'https://mikamike.fr/wp-content/uploads/2026/09/Image-ChatGPT-27-sept.-2026-13_45_05-2.png',
    localUrl: '/assets/illustrations/593_Image-ChatGPT-27-sept.-2026-13_45_05-2.png',
    title: 'Mika et la méthode "Comprends, Entraîne-toi, Progressez !"',
    alt: 'Mika désignant un ordinateur avec le pouce levé et des notes explicatives pas à pas',
    aspectRatio: '16/9',
    useCases: ['methode', 'interface_mika', 'accueil_eleve']
  },
  PRACTICE_PROGRESS: {
    id: 592,
    date: '2026-09-27',
    remoteUrl: 'https://mikamike.fr/wp-content/uploads/2026/09/Image-ChatGPT-27-sept.-2026-13_45_07-3.png',
    localUrl: '/assets/illustrations/592_Image-ChatGPT-27-sept.-2026-13_45_07-3.png',
    title: 'Mika avec son cahier d\'exercices et stylo',
    alt: 'Mika tenant un stylo devant un cahier d\'apprentissage interactif avec corrections claires',
    aspectRatio: '16/9',
    useCases: ['progression', 'exercices_interactifs', 'suivi']
  },
  AI_TUTOR_EUREKA: {
    id: 591,
    date: '2026-09-27',
    remoteUrl: 'https://mikamike.fr/wp-content/uploads/2026/09/Image-ChatGPT-27-sept.-2026-13_45_09-4.png',
    localUrl: '/assets/illustrations/591_Image-ChatGPT-27-sept.-2026-13_45_09-4.png',
    title: 'Mika le professeur IA - Pose "Eureka !" devant le tableau',
    alt: 'Mika levant le doigt pour expliquer un concept scientifique devant un tableau noir et un poster motivant',
    aspectRatio: '16/9',
    useCases: ['interface_mika', 'chat_assistant', 'explication']
  },
  CYCLE_SELECTOR_3D: {
    id: 590,
    date: '2026-09-27',
    remoteUrl: 'https://mikamike.fr/wp-content/uploads/2026/09/Image-ChatGPT-27-sept.-2026-13_45_11-5.png',
    localUrl: '/assets/illustrations/590_Image-ChatGPT-27-sept.-2026-13_45_11-5.png',
    title: 'Présentation des 3 niveaux : Primaire, Collège, Lycée',
    alt: 'Mika devant les 3 cartes de parcours scolaires : Primaire (ampoule), Collège (cahier), Lycée (chapeau de diplômé)',
    aspectRatio: '16/9',
    useCases: ['parcours_primaire', 'college', 'lycee_general', 'lycee_techno', 'choix_niveaux']
  },
  LOGIN_AUTH_CTA: {
    id: 589,
    date: '2026-09-27',
    remoteUrl: 'https://mikamike.fr/wp-content/uploads/2026/09/Image-ChatGPT-27-sept.-2026-13_45_14-6.png',
    localUrl: '/assets/illustrations/589_Image-ChatGPT-27-sept.-2026-13_45_14-6.png',
    title: 'Écran de bienvenue, Connexion & Avantages',
    alt: 'Mika le chat avec bouton d\'action vert et badges de fonctionnalités conforme Éducation nationale',
    aspectRatio: '16/9',
    useCases: ['ecran_connexion', 'inscription', 'landing_cta']
  },
  SUBJECTS_GAMIFIED: {
    id: 588,
    date: '2026-09-27',
    remoteUrl: 'https://mikamike.fr/wp-content/uploads/2026/09/Image-ChatGPT-27-sept.-2026-13_45_16-7.png',
    localUrl: '/assets/illustrations/588_Image-ChatGPT-27-sept.-2026-13_45_16-7.png',
    title: 'Les sciences deviennent un jeu avec Mika',
    alt: 'Mika sur une pile de manuels de Mathématiques, Physique-Chimie et SVT avec bulle de dialogue dynamique',
    aspectRatio: '16/9',
    useCases: ['choix_matieres', 'gamification', 'parcours_primaire']
  },

  // --- 2. ENSEIGNANTS PAR MATIÈRES (PHOTORÉALISTE / CLASSIQUE) ---
  MATHS_PROF: {
    id: 439,
    remoteUrl: 'https://mikamike.fr/wp-content/uploads/2026/07/11-mika-prof-maths-complet.jpg',
    localUrl: '/assets/illustrations/439_11-mika-prof-maths-complet.jpg',
    title: 'Mika Professeur de Mathématiques',
    alt: 'Mika le chat tigré désignant des équations mathématiques, géométrie et théorèmes au tableau',
    aspectRatio: '4/3',
    subjectId: 'maths',
    useCases: ['choix_matieres', 'maths_header', 'lycee_general']
  },
  PHYSICS_PROF: {
    id: 453,
    remoteUrl: 'https://mikamike.fr/wp-content/uploads/2026/07/12-mika-prof-physique-1.jpg',
    localUrl: '/assets/illustrations/453_12-mika-prof-physique-1.jpg',
    title: 'Mika Professeur de Physique',
    alt: 'Mika le chat tigré avec un tableau de formules de mécanique, pendule et lois de Newton',
    aspectRatio: '4/3',
    subjectId: 'physique',
    useCases: ['choix_matieres', 'physique_header', 'college', 'lycee_techno']
  },
  CHEMISTRY_PROF: {
    id: 449,
    remoteUrl: 'https://mikamike.fr/wp-content/uploads/2026/07/08-mika-prof-chimie-1.jpg',
    localUrl: '/assets/illustrations/449_08-mika-prof-chimie-1.jpg',
    title: 'Mika Professeur de Chimie',
    alt: 'Mika le chat tigré dans un laboratoire avec éprouvettes colorées et réactions chimiques',
    aspectRatio: '4/3',
    subjectId: 'chimie',
    useCases: ['choix_matieres', 'chimie_header', 'lycee_techno']
  },
  SVT_PROF: {
    id: 454,
    remoteUrl: 'https://mikamike.fr/wp-content/uploads/2026/07/13-mika-prof-svt-1.jpg',
    localUrl: '/assets/illustrations/454_13-mika-prof-svt-1.jpg',
    title: 'Mika Professeur de SVT',
    alt: 'Mika le chat tigré expliquant la cellule végétale, l\'ADN et la biologie au tableau avec microscope',
    aspectRatio: '4/3',
    subjectId: 'svt',
    useCases: ['choix_matieres', 'svt_header', 'college', 'parcours_primaire']
  },

  // --- 3. ESPACE PARENT & AMBIANCE FAMILIALE ---
  PARENT_FAMILY: {
    id: 422,
    remoteUrl: 'https://mikamike.fr/wp-content/uploads/2026/07/mika-famille-maths-wordpress-1.jpg',
    localUrl: '/assets/illustrations/422_mika-famille-maths-wordpress-1.jpg',
    title: 'Mika - Apprentissage en famille',
    alt: 'Père et ses enfants faisant leurs devoirs de sciences et maths en famille avec Mika le chat rassurant',
    aspectRatio: '4/3',
    useCases: ['espace_parent', 'reassurance_parentale', 'temoignages']
  },

  // --- 4. AVATARS, AMBIANCE DE TRAVAIL & ÉTATS VIDES ---
  AVATAR_WELCOME: {
    id: 534,
    remoteUrl: 'https://mikamike.fr/wp-content/uploads/2026/07/avatar-accueil.webp',
    localUrl: '/assets/illustrations/534_avatar-accueil.webp',
    title: 'Avatar de Mika le chat professeur',
    alt: 'Avatar debout de Mika le chat avec son nœud papillon et étoiles étincelantes',
    aspectRatio: '3/5',
    useCases: ['avatar', 'modal_bienvenue', 'etat_vide', 'chargement']
  },
  LOGO_PORTRAIT: {
    id: 475,
    remoteUrl: 'https://mikamike.fr/wp-content/uploads/2026/07/cropped-cropped-03-mika-portrait-logo-1.jpg',
    localUrl: '/assets/illustrations/475_cropped-cropped-03-mika-portrait-logo-1.jpg',
    title: 'Logo Portrait Mika',
    alt: 'Portrait officiel de Mika le chat mascotte MikaMike',
    aspectRatio: '1/1',
    useCases: ['header_logo', 'favicon', 'badge_prof']
  },
  DESK_AMBIANCE: {
    id: 450,
    remoteUrl: 'https://mikamike.fr/wp-content/uploads/2026/07/09-mika-au-bureau-1.jpg',
    localUrl: '/assets/illustrations/450_09-mika-au-bureau-1.jpg',
    title: 'Mika à son bureau de travail',
    alt: 'Mika le chat allongé sereinement sur un bureau avec cahier de mathématiques et lampe',
    aspectRatio: '16/9',
    useCases: ['etat_attente', 'pause_etude', 'a_propos']
  }
};

/**
 * Helper sécurisé pour récupérer une URL d'image avec fallback local automatique
 */
export function getMediaSource(mediaObj) {
  if (!mediaObj) return '';
  return mediaObj.remoteUrl || mediaObj.localUrl;
}
