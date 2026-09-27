import React from 'react';
import { MIKAMIKE_MEDIA } from '../../data/mikamikeMedia';
import ResponsiveIllustration from '../core/ResponsiveIllustration';
import { Award, CheckCircle2, TrendingUp, Sparkles, BookOpen, Clock, Flame } from 'lucide-react';

export default function ProgressView({ selectedLevel, selectedSubject }) {
  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      
      {/* Top Banner (WP ID 592) */}
      <div className="glass-card" style={{
        padding: '1.75rem',
        borderRadius: '20px',
        background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(249, 115, 22, 0.15))',
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
            <TrendingUp size={14} /> Suivi & Tableau de Bord Élève
          </div>

          <h2 style={{ fontSize: '2rem', fontWeight: '800', color: '#f8fafc' }}>
            Je comprends, je m'entraîne, je <span style={{ color: '#34d399' }}>progresse</span> !
          </h2>

          <p style={{ color: '#94a3b8', fontSize: '0.95rem', lineHeight: 1.6 }}>
            Suis ton rythme d'apprentissage, gagne des badges de réussite et valide tes chapitres un à un avec les conseils personnalisés de Mika.
          </p>

          <div style={{ display: 'flex', gap: '1.5rem', marginTop: '0.5rem' }}>
            <div>
              <div style={{ fontSize: '1.5rem', fontWeight: '900', color: '#34d399' }}>85%</div>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Taux de réussite</div>
            </div>
            <div style={{ width: '1px', background: '#334155' }} />
            <div>
              <div style={{ fontSize: '1.5rem', fontWeight: '900', color: '#38bdf8' }}>14</div>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Exercices réussis</div>
            </div>
            <div style={{ width: '1px', background: '#334155' }} />
            <div>
              <div style={{ fontSize: '1.5rem', fontWeight: '900', color: '#f97316' }}>5 jours</div>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Série en cours 🔥</div>
            </div>
          </div>
        </div>

        <div>
          <ResponsiveIllustration
            media={MIKAMIKE_MEDIA.PRACTICE_PROGRESS}
            aspectRatio="16/9"
            altOverride="Mika avec son cahier d'exercices et stylo - WP ID 592"
          />
        </div>
      </div>

      {/* Progress Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem' }}>
        <div className="glass-card" style={{ padding: '1.5rem', borderRadius: '16px', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Award size={24} color="#34d399" />
            <h3 style={{ fontSize: '1.1rem', fontWeight: '700', color: '#f8fafc' }}>Badges Débloqués</h3>
          </div>
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            <span style={{ background: 'rgba(16, 185, 129, 0.2)', color: '#34d399', padding: '6px 12px', borderRadius: '8px', fontSize: '0.8rem', fontWeight: '700' }}>
              🎯 Champion des Équations
            </span>
            <span style={{ background: 'rgba(2, 132, 199, 0.2)', color: '#38bdf8', padding: '6px 12px', borderRadius: '8px', fontSize: '0.8rem', fontWeight: '700' }}>
              ⚡ Expert en Forces & Mouvement
            </span>
            <span style={{ background: 'rgba(249, 115, 22, 0.2)', color: '#f97316', padding: '6px 12px', borderRadius: '8px', fontSize: '0.8rem', fontWeight: '700' }}>
              🔬 As du Laboratoire Chimie
            </span>
          </div>
        </div>

        <div className="glass-card" style={{ padding: '1.5rem', borderRadius: '16px', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Clock size={24} color="#38bdf8" />
            <h3 style={{ fontSize: '1.1rem', fontWeight: '700', color: '#f8fafc' }}>Dernières Sessions</h3>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.85rem', color: '#cbd5e1' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #334155' }}>
              <span>Maths - Pivot de Gauss</span>
              <span style={{ color: '#34d399', fontWeight: '700' }}>20/20</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #334155' }}>
              <span>Physique - Lois de Newton</span>
              <span style={{ color: '#38bdf8', fontWeight: '700' }}>18/20</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0' }}>
              <span>SVT - Génétique & ADN</span>
              <span style={{ color: '#f97316', fontWeight: '700' }}>17/20</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
