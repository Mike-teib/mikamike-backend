import React from 'react';
import { MIKAMIKE_MEDIA } from '../../data/mikamikeMedia';
import ResponsiveIllustration from '../core/ResponsiveIllustration';
import { Coffee, Sparkles, RefreshCw, Search } from 'lucide-react';

export default function EmptyStatesView({ type = 'pause', onRetry }) {
  if (type === 'search_empty') {
    return (
      <div className="glass-card" style={{
        maxWidth: '600px',
        margin: '2rem auto',
        padding: '2rem',
        borderRadius: '16px',
        textAlign: 'center',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '1.25rem'
      }}>
        <div style={{ maxWidth: '280px', margin: '0 auto' }}>
          <ResponsiveIllustration
            media={MIKAMIKE_MEDIA.AVATAR_WELCOME}
            aspectRatio="3/4"
            altOverride="Mika avatar - Aucun résultat trouvé - WP ID 534"
          />
        </div>

        <h3 style={{ fontSize: '1.2rem', fontWeight: '700', color: '#f8fafc' }}>
          Aucun exercice ne correspond à cette recherche
        </h3>

        <p style={{ fontSize: '0.85rem', color: '#94a3b8' }}>
          Essayez de modifier vos filtres de chapitre ou demandez directement conseil à Mika dans le chat IA !
        </p>

        <button
          onClick={onRetry}
          className="btn btn-primary"
          style={{ background: '#10b981', border: 'none', padding: '0.65rem 1.25rem', borderRadius: '8px' }}
        >
          <RefreshCw size={16} /> Réinitialiser les filtres
        </button>
      </div>
    );
  }

  // Default: Pause / Study Break Empty State (WP ID 450)
  return (
    <div className="glass-card" style={{
      maxWidth: '750px',
      margin: '2rem auto',
      padding: '2rem',
      borderRadius: '20px',
      background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(6, 182, 212, 0.1))',
      border: '1px solid rgba(6, 182, 212, 0.2)',
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
      gap: '1.5rem',
      alignItems: 'center'
    }}>
      <div>
        <ResponsiveIllustration
          media={MIKAMIKE_MEDIA.DESK_AMBIANCE}
          aspectRatio="16/9"
          altOverride="Mika le chat au bureau de travail - WP ID 450"
        />
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', color: '#38bdf8', fontSize: '0.8rem', fontWeight: '700' }}>
          <Coffee size={16} /> Temps de Pause & Réflexion
        </div>

        <h3 style={{ fontSize: '1.4rem', fontWeight: '800', color: '#f8fafc' }}>
          Fais une petite pause, Mika garde tes notes ! ☕
        </h3>

        <p style={{ fontSize: '0.85rem', color: '#94a3b8', lineHeight: 1.5 }}>
          Reprendre des forces est essentiel pour assimiler les concepts de sciences et de maths. Dès que tu es prêt, clique ci-dessous.
        </p>

        <button
          onClick={onRetry}
          className="btn"
          style={{
            background: 'linear-gradient(135deg, #10b981, #0284c7)',
            color: '#fff',
            fontWeight: '700',
            border: 'none',
            padding: '0.75rem 1.25rem',
            borderRadius: '10px',
            marginTop: '0.5rem'
          }}
        >
          <Sparkles size={16} /> Reprendre la séance d'entraînement
        </button>
      </div>
    </div>
  );
}
