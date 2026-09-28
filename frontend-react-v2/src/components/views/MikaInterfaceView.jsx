import React from 'react';
import { MIKAMIKE_MEDIA } from '../../data/mikamikeMedia';
import ResponsiveIllustration from '../core/ResponsiveIllustration';
import ChatInterface from '../core/ChatInterface';
import { Sparkles, MessageSquare, Lightbulb, Zap, ShieldCheck } from 'lucide-react';

export default function MikaInterfaceView({ activeSubject, activeLevel, activeExercise, inputFormula, onInputChange }) {
  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      
      {/* Top Banner (WP ID 591) */}
      <div className="glass-card" style={{
        padding: '1.5rem',
        borderRadius: '20px',
        background: 'linear-gradient(135deg, rgba(2, 132, 199, 0.15), rgba(16, 185, 129, 0.15))',
        border: '1px solid rgba(2, 132, 199, 0.3)',
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
        gap: '1.5rem',
        alignItems: 'center'
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
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
            <Sparkles size={14} /> Mika - Ton Assistant IA Pédagogique
          </div>

          <h2 style={{ fontSize: '1.8rem', fontWeight: '800', color: '#f8fafc' }}>
            Pose ta question à <span style={{ color: '#34d399' }}>Mika</span> !
          </h2>

          <p style={{ color: '#94a3b8', fontSize: '0.9rem', lineHeight: 1.5 }}>
            Une hésitation sur un théorème ? Un problème de physique-chimie ou de SVT à résoudre ? Mika t'explique étape par étape sans te donner la réponse brute.
          </p>

          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', fontSize: '0.8rem', color: '#cbd5e1' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}><Lightbulb size={14} color="#34d399" /> Explications visuelles</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}><Zap size={14} color="#38bdf8" /> Réponses adaptées au niveau</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}><ShieldCheck size={14} color="#f97316" /> Bienveillant & sécurisé</span>
          </div>
        </div>

        <div>
          <ResponsiveIllustration
            media={MIKAMIKE_MEDIA.AI_TUTOR_EUREKA}
            aspectRatio="16/9"
            altOverride="Mika le professeur IA - Eureka pose devant le tableau - WP ID 591"
          />
        </div>
      </div>

      {/* Main Interactive Chat Stage */}
      <div style={{ height: '580px', borderRadius: '16px', overflow: 'hidden' }}>
        <ChatInterface
          activeSubject={activeSubject}
          activeLevel={activeLevel}
          activeExercise={activeExercise}
          inputFormula={inputFormula}
          onInputChange={onInputChange}
        />
      </div>
    </div>
  );
}
