import React, { useState } from 'react';
import { Info, Settings, CheckCircle2, ShieldCheck } from 'lucide-react';

/**
 * ProgramAdminBar Component:
 * Displays active curriculum program version without distracting students,
 * while offering a local admin/debug bar toggle for inspecting version details.
 */
export default function ProgramAdminBar({ meta }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div style={{ background: '#0b1120', borderBottom: '1px solid #1e293b', fontSize: '0.8rem', padding: '0.35rem 1.25rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#94a3b8' }}>
          <CheckCircle2 size={14} color="#34d399" />
          <span>Programme actif : <strong>{meta.school_year}</strong> ({meta.bo_version})</span>
        </div>

        <button
          onClick={() => setIsOpen(!isOpen)}
          className="btn btn-outline"
          style={{ padding: '2px 8px', fontSize: '0.75rem', height: '24px' }}
          aria-expanded={isOpen}
          aria-label="Toggle UI Admin Debug Panel"
        >
          <Settings size={12} />
          <span>{isOpen ? 'Masquer Admin' : 'Debug Admin'}</span>
        </button>
      </div>

      {/* Expandable Local Admin / Debug Panel */}
      {isOpen && (
        <div className="glass-card" style={{ marginTop: '0.5rem', padding: '0.75rem 1rem', background: '#1e293b', borderColor: '#3b82f6' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', color: '#60a5fa', fontWeight: '600' }}>
            <ShieldCheck size={16} />
            <span>UI Admin Local / Métadonnées du Programme Canonique</span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem', fontSize: '0.8rem' }}>
            <div>
              <span style={{ color: '#94a3b8' }}>Version de la maquette:</span> <strong style={{ color: '#f8fafc' }}>{meta.version}</strong>
            </div>
            <div>
              <span style={{ color: '#94a3b8' }}>Référence BO:</span> <strong style={{ color: '#f8fafc' }}>{meta.bo_version}</strong>
            </div>
            <div>
              <span style={{ color: '#94a3b8' }}>Année Scolaire:</span> <strong style={{ color: '#f8fafc' }}>{meta.school_year}</strong>
            </div>
            <div>
              <span style={{ color: '#94a3b8' }}>Statut Source:</span> <span className="badge-disponible">{meta.source_status}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
