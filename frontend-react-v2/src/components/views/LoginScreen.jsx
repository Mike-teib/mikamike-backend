import React, { useState } from 'react';
import { MIKAMIKE_MEDIA } from '../../data/mikamikeMedia';
import ResponsiveIllustration from '../core/ResponsiveIllustration';
import { LogIn, UserCheck, ShieldCheck, Sparkles, ArrowRight } from 'lucide-react';

export default function LoginScreen({ onLoginSuccess }) {
  const [email, setEmail] = useState('eleve.demo@mikamike.fr');
  const [password, setPassword] = useState('••••••••');
  const [role, setRole] = useState('eleve'); // 'eleve' | 'parent'

  const handleSubmit = (e) => {
    e.preventDefault();
    if (onLoginSuccess) onLoginSuccess({ email, role });
  };

  return (
    <div style={{
      maxWidth: '1150px',
      margin: '0 auto',
      padding: '1.5rem 1rem',
      display: 'flex',
      flexDirection: 'column',
      gap: '2rem'
    }}>
      {/* Top Banner Hero from WP ID 589 */}
      <div className="glass-card" style={{
        padding: '1.5rem',
        borderRadius: '16px',
        background: 'linear-gradient(135deg, rgba(6, 182, 212, 0.15), rgba(16, 185, 129, 0.15))',
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
            border: '1px solid rgba(16, 185, 129, 0.4)',
            color: '#34d399',
            padding: '4px 12px',
            borderRadius: '9999px',
            fontSize: '0.8rem',
            fontWeight: '700',
            width: 'fit-content'
          }}>
            <Sparkles size={14} /> Plateforme Conforme Éducation Nationale
          </div>

          <h2 style={{ fontSize: '1.8rem', fontWeight: '800', lineHeight: 1.2, color: '#f8fafc' }}>
            Bienvenue sur <span style={{ color: '#34d399' }}>MikaMike</span> !
          </h2>

          <p style={{ color: '#94a3b8', fontSize: '0.95rem', lineHeight: 1.6 }}>
            Accède à tes exercices interactifs, à la méthode pas à pas et au coaching bienveillant de Mika le chat professeur pour réussir en maths et en sciences.
          </p>

          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginTop: '0.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#38bdf8', fontSize: '0.85rem', fontWeight: '600' }}>
              <ShieldCheck size={16} /> Suivi de progression clair
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#f97316', fontSize: '0.85rem', fontWeight: '600' }}>
              <UserCheck size={16} /> Espace sécurisé parents
            </div>
          </div>
        </div>

        {/* Real WP Illustration ID 589 */}
        <div>
          <ResponsiveIllustration
            media={MIKAMIKE_MEDIA.LOGIN_AUTH_CTA}
            aspectRatio="16/9"
            altOverride="Écran de connexion et avantages MikaMike - Illustration officielle WordPress ID 589"
          />
        </div>
      </div>

      {/* Main Login Form Container */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
        gap: '2rem',
        alignItems: 'start'
      }}>
        {/* Form Card */}
        <div className="glass-card" style={{ padding: '2rem', borderRadius: '16px', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ fontSize: '1.3rem', fontWeight: '700', color: '#f8fafc' }}>
              Se connecter
            </h3>
            <span style={{ fontSize: '0.8rem', color: '#0284c7', background: 'rgba(2, 132, 199, 0.15)', padding: '2px 8px', borderRadius: '6px', fontWeight: '600' }}>
              Accès Élève & Parent
            </span>
          </div>

          {/* Role Toggle Switcher */}
          <div style={{ display: 'flex', background: '#0f172a', borderRadius: '10px', padding: '4px', border: '1px solid #334155' }}>
            <button
              type="button"
              onClick={() => setRole('eleve')}
              style={{
                flex: 1,
                padding: '8px',
                borderRadius: '8px',
                border: 'none',
                background: role === 'eleve' ? 'linear-gradient(135deg, #10b981, #059669)' : 'transparent',
                color: role === 'eleve' ? '#fff' : '#94a3b8',
                fontWeight: '700',
                fontSize: '0.85rem',
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
            >
              🎒 Espace Élève
            </button>
            <button
              type="button"
              onClick={() => setRole('parent')}
              style={{
                flex: 1,
                padding: '8px',
                borderRadius: '8px',
                border: 'none',
                background: role === 'parent' ? 'linear-gradient(135deg, #0284c7, #0369a1)' : 'transparent',
                color: role === 'parent' ? '#fff' : '#94a3b8',
                fontWeight: '700',
                fontSize: '0.85rem',
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
            >
              👨‍👩‍👧 Espace Parent
            </button>
          </div>

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '600', color: '#94a3b8', marginBottom: '0.35rem' }}>
                Adresse Email ou Identifiant MikaMike
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.75rem 1rem',
                  borderRadius: '8px',
                  background: '#0f172a',
                  border: '1px solid #334155',
                  color: '#fff',
                  fontSize: '0.9rem'
                }}
                required
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '600', color: '#94a3b8', marginBottom: '0.35rem' }}>
                Mot de passe
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.75rem 1rem',
                  borderRadius: '8px',
                  background: '#0f172a',
                  border: '1px solid #334155',
                  color: '#fff',
                  fontSize: '0.9rem'
                }}
                required
              />
            </div>

            <button
              type="submit"
              className="btn"
              style={{
                marginTop: '0.5rem',
                padding: '0.85rem',
                borderRadius: '10px',
                background: 'linear-gradient(135deg, #10b981, #0284c7)',
                color: '#fff',
                fontWeight: '700',
                fontSize: '0.95rem',
                border: 'none',
                boxShadow: '0 4px 15px rgba(16, 185, 129, 0.35)'
              }}
            >
              <LogIn size={18} /> Se connecter à mon espace <ArrowRight size={18} />
            </button>
          </form>
        </div>

        {/* Secondary Illustration Card ID 591 */}
        <div className="glass-card" style={{ padding: '1.5rem', borderRadius: '16px', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <h4 style={{ fontSize: '1rem', fontWeight: '700', color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Sparkles size={16} /> Mika est prêt à t'aider !
          </h4>

          <ResponsiveIllustration
            media={MIKAMIKE_MEDIA.AI_TUTOR_EUREKA}
            aspectRatio="16/9"
            altOverride="Mika le professeur IA - Illustration officielle WordPress ID 591"
          />

          <p style={{ fontSize: '0.85rem', color: '#94a3b8', lineHeight: 1.5 }}>
            « Avec moi, pas de stress ! Je t'explique chaque concept à ton rythme avec des vidéos, du soutien interactif et des corrections guidées. »
          </p>
        </div>
      </div>
    </div>
  );
}
