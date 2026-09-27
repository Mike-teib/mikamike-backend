import React, { useState } from 'react';
import { Award, FileText, CheckCircle2, Clock, AlertCircle } from 'lucide-react';

/**
 * ExamMode Component:
 * Prototype for Brevet (DNB) & Baccalauréat annales browser.
 * Filters by exam type (Brevet / Bac), Year, Session, Subject, with exercise lists & barèmes.
 */
export default function ExamMode({ curriculum }) {
  const [examType, setExamType] = useState('All');
  const [selectedYear, setSelectedYear] = useState('All');
  const [selectedAnnale, setSelectedAnnale] = useState(curriculum.exam_annales[0]);

  const filteredAnnales = curriculum.exam_annales.filter(item => {
    if (examType !== 'All' && item.exam_type !== examType) return false;
    if (selectedYear !== 'All' && item.year.toString() !== selectedYear) return false;
    return true;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', height: '100%', overflowY: 'auto', padding: '1.25rem' }}>
      {/* Exam Header Banner */}
      <div className="glass-card" style={{ padding: '1.25rem', background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.9), rgba(51, 65, 85, 0.7))' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
          <Award size={28} color="#fbbf24" />
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: '700' }}>Mode Examen — Annales Officielles (Brevet & Bac)</h2>
            <p style={{ fontSize: '0.85rem', color: '#94a3b8' }}>Entraînement guidé sur sujets réels d'examens nationaux avec corrigés détaillés et barème.</p>
          </div>
        </div>

        {/* Filter Toolbar */}
        <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem', flexWrap: 'wrap' }}>
          <div className="selector-group">
            <label htmlFor="exam-type-filter" className="selector-label">Examen</label>
            <select
              id="exam-type-filter"
              className="selector-select"
              value={examType}
              onChange={(e) => setExamType(e.target.value)}
            >
              <option value="All">Tous les examens</option>
              <option value="Brevet">Brevet (DNB)</option>
              <option value="Bac">Baccalauréat</option>
            </select>
          </div>

          <div className="selector-group">
            <label htmlFor="exam-year-filter" className="selector-label">Année</label>
            <select
              id="exam-year-filter"
              className="selector-select"
              value={selectedYear}
              onChange={(e) => setSelectedYear(e.target.value)}
            >
              <option value="All">Toutes les années</option>
              <option value="2024">2024</option>
              <option value="2023">2023</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Grid: Annales List & Detail View */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.25rem' }}>
        {/* Left Column: List of Subjects */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: '600', color: '#94a3b8' }}>Sujets Disponibles ({filteredAnnales.length})</h3>
          {filteredAnnales.map(annale => {
            const isSelected = selectedAnnale?.id === annale.id;
            return (
              <div
                key={annale.id}
                onClick={() => setSelectedAnnale(annale)}
                className="glass-card"
                style={{
                  padding: '1rem',
                  cursor: 'pointer',
                  borderColor: isSelected ? '#3b82f6' : undefined,
                  borderLeft: isSelected ? '4px solid #3b82f6' : undefined,
                  transition: 'all 0.2s ease'
                }}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && setSelectedAnnale(annale)}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                  <span style={{ fontSize: '0.75rem', fontWeight: '700', textTransform: 'uppercase', color: '#60a5fa' }}>
                    {annale.exam_type} {annale.year} — {annale.session}
                  </span>
                  <span className={annale.coverage === 'Disponible' ? 'badge-disponible' : annale.coverage === 'Partiel' ? 'badge-partiel' : 'badge-preparation'}>
                    {annale.coverage}
                  </span>
                </div>
                <h4 style={{ fontSize: '0.95rem', fontWeight: '600', marginBottom: '0.35rem' }}>{annale.title}</h4>
                <div style={{ display: 'flex', gap: '1rem', fontSize: '0.8rem', color: '#94a3b8' }}>
                  <span><Clock size={12} style={{ display: 'inline', marginRight: '4px' }} />{annale.duration}</span>
                  <span><Award size={12} style={{ display: 'inline', marginRight: '4px' }} />{annale.points} points</span>
                  <span>{annale.level}</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Right Column: Selected Annale Detail */}
        {selectedAnnale && (
          <div className="glass-card" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ borderBottom: '1px solid #334155', pb: '0.75rem' }}>
              <span className="badge-disponible" style={{ marginBottom: '0.5rem', display: 'inline-block' }}>
                {selectedAnnale.exam_type} • {selectedAnnale.subject}
              </span>
              <h3 style={{ fontSize: '1.15rem', fontWeight: '700' }}>{selectedAnnale.title}</h3>
              <p style={{ fontSize: '0.85rem', color: '#94a3b8', marginTop: '0.25rem' }}>
                Session {selectedAnnale.session} {selectedAnnale.year} | Niveau : {selectedAnnale.level} | Durée : {selectedAnnale.duration}
              </p>
            </div>

            {/* Exercise Breakdown */}
            <div>
              <h4 style={{ fontSize: '0.95rem', fontWeight: '600', marginBottom: '0.75rem', color: '#f8fafc' }}>
                Structure de l'épreuve ({selectedAnnale.exercises.length} exercices)
              </h4>
              {selectedAnnale.exercises.length === 0 ? (
                <div style={{ padding: '1.5rem', textAlign: 'center', background: 'rgba(244, 63, 94, 0.1)', borderRadius: '8px', border: '1px solid rgba(244, 63, 94, 0.3)' }}>
                  <AlertCircle size={24} color="#fda4af" style={{ margin: '0 auto 0.5rem' }} />
                  <p style={{ fontSize: '0.9rem', color: '#fda4af', fontWeight: '600' }}>Épreuve en préparation</p>
                  <p style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Les exercices et corrigés officiels pour ce sujet sont en cours d'intégration.</p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {selectedAnnale.exercises.map(ex => (
                    <div key={ex.id} style={{ background: '#0f172a', padding: '0.75rem 1rem', borderRadius: '8px', border: '1px solid #334155', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <div style={{ fontWeight: '600', fontSize: '0.875rem' }}>{ex.title}</div>
                        <span style={{ fontSize: '0.75rem', color: '#60a5fa' }}>ID: {ex.id}</span>
                      </div>
                      <span className="badge-disponible">{ex.points} pts</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {selectedAnnale.exercises.length > 0 && (
              <button className="btn btn-primary" style={{ marginTop: 'auto' }}>
                Lancer la session d'entraînement Examen
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
