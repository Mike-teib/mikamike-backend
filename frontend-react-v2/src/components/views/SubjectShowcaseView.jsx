import React from 'react';
import { MIKAMIKE_MEDIA } from '../../data/mikamikeMedia';
import ResponsiveIllustration from '../core/ResponsiveIllustration';
import { BookOpen, Sparkles, ArrowRight, Check } from 'lucide-react';

export default function SubjectShowcaseView({ selectedSubject, onSelectSubject, onStartExercises }) {
  const subjectsList = [
    {
      id: 'maths',
      title: 'Mathématiques',
      subtitle: 'Algèbre, Géométrie, Analyse, Probabilités',
      media: MIKAMIKE_MEDIA.MATHS_PROF,
      badgeColor: '#0284c7',
      bgGlow: 'rgba(2, 132, 199, 0.15)',
      description: 'Maîtrise le calcul, la résolution d\'équations et les théorèmes fondamentaux avec des cours structurés.'
    },
    {
      id: 'physique',
      title: 'Physique',
      subtitle: 'Mécanique, Électricité, Forces, Ondes & Optique',
      media: MIKAMIKE_MEDIA.PHYSICS_PROF,
      badgeColor: '#10b981',
      bgGlow: 'rgba(16, 185, 129, 0.15)',
      description: 'Comprends les lois de l\'univers, les forces et le mouvement grâce à des schémas et démonstrations interactives.'
    },
    {
      id: 'chimie',
      title: 'Chimie',
      subtitle: 'Réactions, Molécules, Solutions & Laboratoire',
      media: MIKAMIKE_MEDIA.CHEMISTRY_PROF,
      badgeColor: '#f97316',
      bgGlow: 'rgba(249, 115, 22, 0.15)',
      description: 'Explore la structure de la matière, les équations de réaction et l\'alchimie des solutions chimiques.'
    },
    {
      id: 'svt',
      title: 'SVT (Sciences de la Vie et de la Terre)',
      subtitle: 'Biologie, Génétique, ADN, Écologie & Géologie',
      media: MIKAMIKE_MEDIA.SVT_PROF,
      badgeColor: '#34d399',
      bgGlow: 'rgba(52, 211, 153, 0.15)',
      description: 'Plonge dans le monde du vivant, le fonctionnement des cellules et la dynamique de la planète Terre.'
    }
  ];

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      {/* Top Banner (WP ID 588) */}
      <div className="glass-card" style={{
        padding: '1.75rem',
        borderRadius: '20px',
        background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(2, 132, 199, 0.15))',
        border: '1px solid rgba(16, 185, 129, 0.3)',
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
        gap: '1.5rem',
        alignItems: 'center'
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.5rem',
            background: 'rgba(16, 185, 129, 0.2)',
            color: '#34d399',
            padding: '4px 12px',
            borderRadius: '9999px',
            fontSize: '0.8rem',
            fontWeight: '700',
            width: 'fit-content'
          }}>
            <Sparkles size={14} /> Toutes tes Matières Scientifiques
          </div>

          <h2 style={{ fontSize: '2rem', fontWeight: '800', lineHeight: 1.2, color: '#f8fafc' }}>
            Avec Mika, les sciences deviennent un <span style={{ color: '#38bdf8' }}>jeu</span> !
          </h2>

          <p style={{ color: '#94a3b8', fontSize: '0.95rem', lineHeight: 1.6 }}>
            Choisis la matière scientifique que tu souhaites travailler. Chaque discipline est enseignée avec pédagogie, bienveillance et une approche pas à pas.
          </p>
        </div>

        <div>
          <ResponsiveIllustration
            media={MIKAMIKE_MEDIA.SUBJECTS_GAMIFIED}
            aspectRatio="16/9"
            altOverride="Les sciences deviennent un jeu avec Mika - Illustration officielle WP ID 588"
          />
        </div>
      </div>

      {/* Grid of Subject Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem' }}>
        {subjectsList.map((subject) => {
          const isSelected = selectedSubject === subject.id;
          return (
            <div
              key={subject.id}
              className="glass-card"
              onClick={() => onSelectSubject && onSelectSubject(subject.id)}
              style={{
                borderRadius: '16px',
                padding: '1.25rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '1rem',
                cursor: 'pointer',
                border: isSelected ? `2px solid ${subject.badgeColor}` : '1px solid rgba(255, 255, 255, 0.1)',
                background: isSelected ? subject.bgGlow : 'rgba(30, 41, 59, 0.7)',
                transition: 'all 0.3s ease',
                position: 'relative'
              }}
            >
              {isSelected && (
                <div style={{
                  position: 'absolute',
                  top: '12px',
                  right: '12px',
                  background: subject.badgeColor,
                  color: '#fff',
                  borderRadius: '50%',
                  width: '24px',
                  height: '24px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  <Check size={14} />
                </div>
              )}

              {/* Subject Specific WP Illustration */}
              <ResponsiveIllustration
                media={subject.media}
                aspectRatio="4/3"
                altOverride={`Enseignant Mika - ${subject.title}`}
              />

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: '700', textTransform: 'uppercase', color: subject.badgeColor, letterSpacing: '0.05em' }}>
                  {subject.subtitle}
                </span>
                <h3 style={{ fontSize: '1.25rem', fontWeight: '800', color: '#f8fafc' }}>
                  {subject.title}
                </h3>
                <p style={{ fontSize: '0.85rem', color: '#94a3b8', lineHeight: 1.5 }}>
                  {subject.description}
                </p>
              </div>

              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectSubject && onSelectSubject(subject.id);
                  onStartExercises && onStartExercises();
                }}
                className="btn"
                style={{
                  marginTop: 'auto',
                  width: '100%',
                  padding: '0.65rem',
                  borderRadius: '10px',
                  background: isSelected ? subject.badgeColor : 'rgba(255, 255, 255, 0.1)',
                  color: '#fff',
                  fontWeight: '700',
                  fontSize: '0.85rem',
                  border: 'none',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.5rem'
                }}
              >
                <BookOpen size={16} /> Explorer les exercices <ArrowRight size={16} />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
