import React from 'react';
import { MIKAMIKE_MEDIA } from '../../data/mikamikeMedia';
import ResponsiveIllustration from '../core/ResponsiveIllustration';
import { Heart, ShieldCheck, UserCheck, Award, Eye, FileText } from 'lucide-react';

export default function ParentSpaceView() {
  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      
      {/* Top Reassurance Hero (WP ID 422) */}
      <div className="glass-card" style={{
        padding: '1.75rem',
        borderRadius: '20px',
        background: 'linear-gradient(135deg, rgba(2, 132, 199, 0.15), rgba(16, 185, 129, 0.15))',
        border: '1px solid rgba(2, 132, 199, 0.3)',
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
        gap: '2rem',
        alignItems: 'center'
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.5rem',
            background: 'rgba(2, 132, 199, 0.2)',
            color: '#38bdf8',
            padding: '4px 12px',
            borderRadius: '9999px',
            fontSize: '0.8rem',
            fontWeight: '700',
            width: 'fit-content'
          }}>
            <Heart size={14} /> Espace Parent & Sérénité Familiale
          </div>

          <h2 style={{ fontSize: '2rem', fontWeight: '800', lineHeight: 1.2, color: '#f8fafc' }}>
            Accompagner ses enfants avec <span style={{ color: '#38bdf8' }}>sérénité</span>
          </h2>

          <p style={{ color: '#94a3b8', fontSize: '0.95rem', lineHeight: 1.6 }}>
            MikaMike aide vos enfants à reprendre confiance en leurs capacités mathématiques et scientifiques, avec des programmes rigoureusement alignés sur l'Éducation Nationale.
          </p>

          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#34d399', fontSize: '0.85rem', fontWeight: '600' }}>
              <ShieldCheck size={18} /> Environnement 100% sécurisé
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#38bdf8', fontSize: '0.85rem', fontWeight: '600' }}>
              <Eye size={18} /> Rapport hebdomadaire par mail
            </div>
          </div>
        </div>

        <div>
          <ResponsiveIllustration
            media={MIKAMIKE_MEDIA.PARENT_FAMILY}
            aspectRatio="4/3"
            altOverride="Mika - Apprentissage des maths en famille - WP ID 422"
          />
        </div>
      </div>

      {/* Parent Portal Controls */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem' }}>
        <div className="glass-card" style={{ padding: '1.5rem', borderRadius: '16px', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <FileText size={24} color="#34d399" />
            <h3 style={{ fontSize: '1.1rem', fontWeight: '700', color: '#f8fafc' }}>Bilan de Révision</h3>
          </div>
          <p style={{ fontSize: '0.85rem', color: '#94a3b8' }}>
            Consultez le temps passé sur chaque matière, le niveau d'autonomie de votre enfant et les notions acquises cette semaine.
          </p>
          <button className="btn btn-outline" style={{ marginTop: 'auto', borderRadius: '8px', fontSize: '0.85rem' }}>
            Télécharger le rapport PDF
          </button>
        </div>

        <div className="glass-card" style={{ padding: '1.5rem', borderRadius: '16px', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Award size={24} color="#f97316" />
            <h3 style={{ fontSize: '1.1rem', fontWeight: '700', color: '#f8fafc' }}>Encouragements</h3>
          </div>
          <p style={{ fontSize: '0.85rem', color: '#94a3b8' }}>
            Laissez un message d'encouragement ou félicitez votre enfant pour ses badges obtenus en mathématiques et physique-chimie.
          </p>
          <button className="btn btn-primary" style={{ marginTop: 'auto', borderRadius: '8px', fontSize: '0.85rem', background: '#0284c7' }}>
            Envoyer un bravo 🎉
          </button>
        </div>
      </div>
    </div>
  );
}
