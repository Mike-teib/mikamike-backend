import React from 'react';
import { MIKAMIKE_MEDIA } from '../../data/mikamikeMedia';
import ResponsiveIllustration from '../core/ResponsiveIllustration';
import { Sparkles, BookOpen, Target, CheckCircle2, ArrowRight, Award, Zap } from 'lucide-react';

export default function StudentHomeView({ onNavigateSection, onSelectLevel, onSelectSubject }) {
  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      
      {/* 1. Main Welcome Hero (WP ID 594) */}
      <div className="glass-card" style={{
        position: 'relative',
        borderRadius: '20px',
        padding: '2rem',
        background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.9), rgba(16, 185, 129, 0.15))',
        border: '1px solid rgba(16, 185, 129, 0.3)',
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
        gap: '2rem',
        alignItems: 'center'
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
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
            <Sparkles size={14} /> Espace Élève MikaMike
          </div>

          <h1 style={{ fontSize: '2.2rem', fontWeight: '900', lineHeight: 1.2, color: '#f8fafc' }}>
            Apprendre les sciences en toute <span style={{ color: '#34d399' }}>confiance</span> !
          </h1>

          <p style={{ color: '#94a3b8', fontSize: '1rem', lineHeight: 1.6 }}>
            Découvre ton parcours personnalisé avec Mika le chat professeur. Du Primaire au Lycée, révise avec des cours clairs, des exercices interactifs et un entraînement adapté à ton niveau.
          </p>

          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
            <button
              onClick={() => onNavigateSection && onNavigateSection('matieres')}
              className="btn"
              style={{
                background: 'linear-gradient(135deg, #10b981, #059669)',
                color: '#fff',
                fontWeight: '700',
                padding: '0.85rem 1.5rem',
                borderRadius: '12px',
                border: 'none',
                boxShadow: '0 4px 15px rgba(16, 185, 129, 0.4)'
              }}
            >
              <BookOpen size={18} /> Choisir ma matière <ArrowRight size={18} />
            </button>

            <button
              onClick={() => onNavigateSection && onNavigateSection('mika')}
              className="btn"
              style={{
                background: 'rgba(2, 132, 199, 0.2)',
                color: '#38bdf8',
                border: '1px solid rgba(2, 132, 199, 0.4)',
                fontWeight: '700',
                padding: '0.85rem 1.5rem',
                borderRadius: '12px'
              }}
            >
              💬 Discuter avec Mika IA
            </button>
          </div>
        </div>

        {/* Real WP Illustration ID 594 */}
        <div>
          <ResponsiveIllustration
            media={MIKAMIKE_MEDIA.LANDING_HERO}
            aspectRatio="16/9"
            altOverride="Vue d'ensemble plateforme MikaMike - Illustration officielle WordPress ID 594"
          />
        </div>
      </div>

      {/* 2. Three Pillars & Method (WP ID 593) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.5rem' }}>
        <div className="glass-card" style={{ padding: '1.5rem', borderRadius: '16px', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{ background: 'rgba(16, 185, 129, 0.2)', padding: '10px', borderRadius: '12px', color: '#34d399' }}>
              <Target size={24} />
            </div>
            <div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: '700', color: '#f8fafc' }}>
                La Méthode MikaMike
              </h3>
              <p style={{ fontSize: '0.8rem', color: '#94a3b8' }}>3 étapes simples pour réussir</p>
            </div>
          </div>

          <ResponsiveIllustration
            media={MIKAMIKE_MEDIA.METHOD_HERO}
            aspectRatio="16/9"
            altOverride="Méthode Mika : Je comprends, Je m'entraîne, Je progresse - WP ID 593"
          />

          <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.5rem', padding: 0 }}>
            <li style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', color: '#e2e8f0' }}>
              <CheckCircle2 size={16} color="#34d399" /> <strong>1. Je comprends</strong> : explications visuelles et intuitives
            </li>
            <li style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', color: '#e2e8f0' }}>
              <CheckCircle2 size={16} color="#38bdf8" /> <strong>2. Je m'entraîne</strong> : exercices interactifs pas à pas
            </li>
            <li style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', color: '#e2e8f0' }}>
              <CheckCircle2 size={16} color="#f97316" /> <strong>3. Je progresse</strong> : conseils personnalisés de Mika
            </li>
          </ul>
        </div>

        {/* 3. Level Showcase Card (WP ID 590) */}
        <div className="glass-card" style={{ padding: '1.5rem', borderRadius: '16px', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{ background: 'rgba(2, 132, 199, 0.2)', padding: '10px', borderRadius: '12px', color: '#38bdf8' }}>
              <Award size={24} />
            </div>
            <div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: '700', color: '#f8fafc' }}>
                Choisis ton Niveau Scolaire
              </h3>
              <p style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Programmes officiels du CP au Lycée</p>
            </div>
          </div>

          <ResponsiveIllustration
            media={MIKAMIKE_MEDIA.CYCLE_SELECTOR_3D}
            aspectRatio="16/9"
            altOverride="Sélecteur des 3 parcours scolaires MikaMike - WP ID 590"
          />

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.5rem' }}>
            <button
              onClick={() => onSelectLevel && onSelectLevel('cm2')}
              style={{
                background: 'rgba(16, 185, 129, 0.15)',
                border: '1px solid rgba(16, 185, 129, 0.3)',
                color: '#34d399',
                padding: '8px',
                borderRadius: '8px',
                fontWeight: '700',
                fontSize: '0.75rem',
                cursor: 'pointer'
              }}
            >
              🌱 Primaire
            </button>
            <button
              onClick={() => onSelectLevel && onSelectLevel('3eme')}
              style={{
                background: 'rgba(2, 132, 199, 0.15)',
                border: '1px solid rgba(2, 132, 199, 0.3)',
                color: '#38bdf8',
                padding: '8px',
                borderRadius: '8px',
                fontWeight: '700',
                fontSize: '0.75rem',
                cursor: 'pointer'
              }}
            >
              🚀 Collège
            </button>
            <button
              onClick={() => onSelectLevel && onSelectLevel('terminale_g')}
              style={{
                background: 'rgba(249, 115, 22, 0.15)',
                border: '1px solid rgba(249, 115, 22, 0.3)',
                color: '#fb923c',
                padding: '8px',
                borderRadius: '8px',
                fontWeight: '700',
                fontSize: '0.75rem',
                cursor: 'pointer'
              }}
            >
              🎓 Lycée
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
