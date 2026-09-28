import React, { useState } from 'react';
import katex from 'katex';
import { Calculator, BookOpen, X } from 'lucide-react';

export default function MathTools({ onClose, onOpenGauss }) {
  const [calcInput, setCalcInput] = useState('');
  const [calcResult, setCalcResult] = useState('');
  const [activeTab, setActiveTab] = useState('calc'); // 'calc' | 'cheatsheet'

  const handleCalcClick = (val) => {
    if (val === 'C') {
      setCalcInput('');
      setCalcResult('');
    } else if (val === '=') {
      try {
        // Safe evaluation of standard math expressions
        const sanitized = calcInput.replace(/×/g, '*').replace(/÷/g, '/');
        // eslint-disable-next-line no-eval
        const res = Function(`"use strict"; return (${sanitized})`)();
        setCalcResult(res.toString());
      } catch (err) {
        setCalcResult('Erreur');
      }
    } else {
      setCalcInput(prev => prev + val);
    }
  };

  const FORMULAS = [
    { title: 'Second degré', math: 'ax^2 + bx + c = 0 \\implies \\Delta = b^2 - 4ac' },
    { title: 'Racines du second degré', math: 'x_{1,2} = \\frac{-b \\pm \\sqrt{\\Delta}}{2a}' },
    { title: 'Dérivée de xⁿ', math: '(x^n)\' = n x^{n-1}' },
    { title: 'Équation de tangente', math: 'y = f\'(a)(x - a) + f(a)' },
    { title: 'Théorème de Pythagore', math: 'AB^2 + AC^2 = BC^2' },
    { title: 'Loi des sinus', math: '\\frac{a}{\\sin A} = \\frac{b}{\\sin B} = \\frac{c}{\\sin C}' }
  ];

  return (
    <div className="glass-card math-tools-panel" style={{ padding: '0.75rem', background: '#0f172a', border: '1px solid #3b82f6', borderRadius: '12px', width: '100%', maxWidth: '320px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', borderBottom: '1px solid #334155', paddingBottom: '0.5rem' }}>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            onClick={() => setActiveTab('calc')}
            className={`btn ${activeTab === 'calc' ? 'btn-primary' : 'btn-outline'}`}
            style={{ padding: '4px 8px', fontSize: '0.8rem' }}
          >
            <Calculator size={14} /> Calculatrice
          </button>
          <button
            onClick={() => setActiveTab('cheatsheet')}
            className={`btn ${activeTab === 'cheatsheet' ? 'btn-primary' : 'btn-outline'}`}
            style={{ padding: '4px 8px', fontSize: '0.8rem' }}
          >
            <BookOpen size={14} /> Formulaire
          </button>
          {onOpenGauss && (
            <button
              onClick={() => {
                onOpenGauss();
                if (onClose) onClose();
              }}
              className="btn btn-outline"
              style={{ padding: '4px 8px', fontSize: '0.8rem', color: '#60a5fa', borderColor: '#3b82f6' }}
            >
              Pivot de Gauss
            </button>
          )}
        </div>
        {onClose && (
          <button onClick={onClose} className="btn btn-outline" style={{ padding: '2px 6px' }} aria-label="Fermer le dialogue d'outils maths">
            <X size={16} />
          </button>
        )}
      </div>

      {activeTab === 'calc' ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {/* Display */}
          <div style={{ background: '#090d16', padding: '0.75rem', borderRadius: '8px', border: '1px solid #334155', textAlign: 'right' }}>
            <div style={{ fontSize: '0.85rem', color: '#94a3b8', minHeight: '1.2rem' }}>{calcInput || '0'}</div>
            <div style={{ fontSize: '1.25rem', fontWeight: '700', color: '#38bdf8', minHeight: '1.8rem' }}>{calcResult || '='}</div>
          </div>

          {/* Calculator Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.35rem' }}>
            {['C', '(', ')', '÷', '7', '8', '9', '×', '4', '5', '6', '-', '1', '2', '3', '+', '0', '.', '='].map(btn => (
              <button
                key={btn}
                onClick={() => handleCalcClick(btn)}
                className={`btn ${btn === '=' ? 'btn-primary' : btn === 'C' ? 'btn-outline' : 'btn-secondary'}`}
                style={{ padding: '0.45rem', fontSize: '0.95rem', gridColumn: btn === '=' ? 'span 2' : 'span 1' }}
                aria-label={`Touche ${btn}`}
              >
                {btn}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '300px', overflowY: 'auto' }}>
          {FORMULAS.map((f, i) => {
            let html = f.math;
            try {
              html = katex.renderToString(f.math, { displayMode: true, throwOnError: false });
            } catch (e) {}
            return (
              <div key={i} style={{ background: '#1e293b', padding: '0.5rem 0.75rem', borderRadius: '6px', border: '1px solid #334155' }}>
                <div style={{ fontSize: '0.75rem', color: '#60a5fa', fontWeight: '600' }}>{f.title}</div>
                <div dangerouslySetInnerHTML={{ __html: html }} />
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
