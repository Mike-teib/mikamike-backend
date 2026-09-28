import React, { useState } from 'react';
import katex from 'katex';
import { RotateCw, ZoomIn, ZoomOut, AlertTriangle, CheckCircle2, FileImage, ShieldAlert, Edit3 } from 'lucide-react';

export default function AsmaPhotoModule({ onConfirmL3 }) {
  const [rotation, setRotation] = useState(0);
  const [zoom, setZoom] = useState(1);
  const [l3ConfirmedValue, setL3ConfirmedValue] = useState('');
  const [l3IsConfirmed, setL3IsConfirmed] = useState(false);

  const handleRotate = () => {
    setRotation(prev => (prev + 90) % 360);
  };

  const handleZoomIn = () => setZoom(prev => Math.min(prev + 0.25, 2.5));
  const handleZoomOut = () => setZoom(prev => Math.max(prev - 0.25, 0.75));

  const handleConfirm = (e) => {
    e?.preventDefault();
    if (l3ConfirmedValue.trim()) {
      setL3IsConfirmed(true);
      if (onConfirmL3) onConfirmL3(l3ConfirmedValue);
    }
  };

  function renderKaTeX(latex) {
    try {
      const html = katex.renderToString(latex, { throwOnError: false });
      return <span dangerouslySetInnerHTML={{ __html: html }} />;
    } catch (e) {
      return <code>{latex}</code>;
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', padding: '1.25rem', color: '#f8fafc', maxWidth: '1100px', margin: '0 auto' }}>
      {/* Banner */}
      <div className="glass-card" style={{ padding: '1.25rem', background: 'linear-gradient(135deg, rgba(30,41,59,0.95), rgba(6,182,212,0.15))', border: '1px solid #06b6d4' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <FileImage size={28} color="#38bdf8" />
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: '800', color: '#38bdf8' }}>
              Module Inspection Photo & Vision Multimodale — Asma
            </h2>
            <p style={{ fontSize: '0.85rem', color: '#94a3b8' }}>
              Prévisualisation sans déformation, rotation interactive et détection stricte des termes masqués.
            </p>
          </div>
        </div>
      </div>

      {/* Main Grid: Original Photo vs What Mika Understood */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '1.25rem' }}>
        {/* Left Box: Photo original avec contrôles de rotation & zoom */}
        <div className="glass-card" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: '700', color: '#38bdf8' }}>1. Photo de Cours Originale (Asma)</h3>
            <div style={{ display: 'flex', gap: '0.35rem' }}>
              <button onClick={handleRotate} className="btn btn-outline" style={{ padding: '4px 8px', fontSize: '0.75rem' }} title="Pivoter de 90°">
                <RotateCw size={14} /> Rotation
              </button>
              <button onClick={handleZoomIn} className="btn btn-outline" style={{ padding: '4px 8px', fontSize: '0.75rem' }} title="Zoomer">
                <ZoomIn size={14} />
              </button>
              <button onClick={handleZoomOut} className="btn btn-outline" style={{ padding: '4px 8px', fontSize: '0.75rem' }} title="Dézoomer">
                <ZoomOut size={14} />
              </button>
            </div>
          </div>

          {/* Simulated Photo Preview Container */}
          <div style={{
            background: '#090d16',
            borderRadius: '10px',
            border: '2px dashed #334155',
            padding: '1.5rem',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '260px',
            overflow: 'hidden',
            position: 'relative'
          }}>
            <div style={{
              transform: `rotate(${rotation}deg) scale(${zoom})`,
              transition: 'transform 0.3s ease',
              textAlign: 'center',
              fontFamily: 'cursive, sans-serif',
              color: '#f1f5f9',
              background: 'rgba(30, 41, 59, 0.9)',
              padding: '1.25rem',
              borderRadius: '8px',
              border: '1px solid #475569',
              boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
              maxWidth: '90%'
            }}>
              <div style={{ fontSize: '0.8rem', color: '#94a3b8', textTransform: 'uppercase', marginBottom: '0.5rem', fontFamily: 'sans-serif' }}>
                📷 Photo de cours manuscrit : PIVOT DE GAUSS
              </div>
              <div style={{ fontSize: '1.1rem', marginBottom: '0.3rem' }}>L1 : x - 5y - 7z = 3</div>
              <div style={{ fontSize: '1.1rem', marginBottom: '0.3rem' }}>L2 : 5x + 3y + 3z = 3</div>
              <div style={{ fontSize: '1.1rem', color: '#fbbf24', background: 'rgba(245, 158, 11, 0.2)', padding: '4px', borderRadius: '4px' }}>
                L3 : <span style={{ textDecoration: 'wavy underline red' }}>[Ombre/Doigt]</span> + 3y + 3z = 3
              </div>
            </div>
          </div>

          <div style={{ fontSize: '0.75rem', color: '#94a3b8', textAlign: 'center' }}>
            Rotation active : {rotation}° | Zoom : {Math.round(zoom * 100)}%
          </div>
        </div>

        {/* Right Box: "Ce que Mika a compris" */}
        <div className="glass-card" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: '700', color: '#38bdf8' }}>2. Ce que Mika a compris</h3>

          <div style={{ background: '#0f172a', padding: '1rem', borderRadius: '8px', border: '1px solid #334155', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid #1e293b', paddingBottom: '0.5rem' }}>
              <span style={{ fontSize: '0.875rem' }}>Ligne 1 ($L_1$) : {renderKaTeX('x - 5y - 7z = 3')}</span>
              <span className="badge-disponible">Certain</span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid #1e293b', paddingBottom: '0.5rem' }}>
              <span style={{ fontSize: '0.875rem' }}>Ligne 2 ($L_2$) : {renderKaTeX('5x + 3y + 3z = 3')}</span>
              <span className="badge-disponible">Certain</span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'rgba(244, 63, 94, 0.1)', padding: '0.5rem', borderRadius: '6px', border: '1px solid rgba(244, 63, 94, 0.3)' }}>
              <span style={{ fontSize: '0.875rem', color: '#fda4af' }}>
                Ligne 3 ($L_3$) : {renderKaTeX('? x + 3y + 3z = 3')}
              </span>
              <span className="badge-preparation" style={{ background: 'rgba(244, 63, 94, 0.3)', color: '#fda4af' }}>
                <ShieldAlert size={12} style={{ display: 'inline', marginRight: '3px' }} /> A CONFIRMER
              </span>
            </div>
          </div>

          {/* Uncertainty Alert & Confirmation Form */}
          {!l3IsConfirmed ? (
            <div style={{ background: 'rgba(245, 158, 11, 0.15)', border: '1px solid #f59e0b', borderRadius: '8px', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#fbbf24', fontWeight: '700', fontSize: '0.9rem' }}>
                <AlertTriangle size={20} />
                <span>Interdiction d'inventer le coefficient masqué</span>
              </div>
              <p style={{ fontSize: '0.85rem', color: '#cbd5e1', lineHeight: '1.4' }}>
                Je lis correctement <strong>L1</strong> et <strong>L2</strong>, mais le premier coefficient devant $x$ dans <strong>L3</strong> est partiellement masqué. Peux-tu me confirmer le premier terme de $L_3$ ?
              </p>

              <form onSubmit={handleConfirm} style={{ display: 'flex', gap: '0.5rem', marginTop: '0.25rem' }}>
                <input
                  type="text"
                  value={l3ConfirmedValue}
                  onChange={(e) => setL3ConfirmedValue(e.target.value)}
                  placeholder="ex: 2x ou -x"
                  style={{ flex: 1, background: '#0f172a', border: '1px solid #334155', color: '#fff', padding: '0.4rem 0.75rem', borderRadius: '6px', fontSize: '0.85rem' }}
                />
                <button type="submit" className="btn btn-primary" style={{ padding: '0.4rem 0.85rem', fontSize: '0.85rem' }}>
                  Confirmer L3
                </button>
              </form>
            </div>
          ) : (
            <div style={{ background: 'rgba(16, 185, 129, 0.15)', border: '1px solid #10b981', borderRadius: '8px', padding: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#34d399' }}>
              <CheckCircle2 size={20} />
              <div>
                <strong>L3 Confirmée par Asma :</strong> {renderKaTeX(`${l3ConfirmedValue} + 3y + 3z = 3`)}
                <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Le système 3x3 est déverrouillé et prêt pour le pivot de Gauss !</div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
