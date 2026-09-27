import React from 'react';
import { Delete, CornerDownLeft } from 'lucide-react';

const KEYBOARD_SYMBOLS = [
  { label: 'x²', latex: 'x^2' },
  { label: 'xⁿ', latex: 'x^{n}' },
  { label: '√x', latex: '\\sqrt{x}' },
  { label: 'a/b', latex: '\\frac{a}{b}' },
  { label: 'Δ', latex: '\\Delta' },
  { label: 'π', latex: '\\pi' },
  { label: '∫', latex: '\\int' },
  { label: 'lim', latex: '\\lim_{x \\to 0}' },
  { label: '≤', latex: '\\le' },
  { label: '≥', latex: '\\ge' },
  { label: '≠', latex: '\\ne' },
  { label: '±', latex: '\\pm' },
  { label: '∞', latex: '\\infty' },
  { label: 'f\'(x)', latex: 'f\'(x)' },
  { label: '∑', latex: '\\sum' }
];

export default function MathKeyboard({ onInsert, onClose }) {
  return (
    <div className="glass-card" style={{ padding: '0.75rem', background: '#0f172a', border: '1px solid #3b82f6', borderRadius: '10px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
        <span style={{ fontSize: '0.8rem', fontWeight: '700', color: '#60a5fa' }}>Clavier Mathématique Éléments Canoniques</span>
        {onClose && (
          <button onClick={onClose} className="btn btn-outline" style={{ padding: '2px 6px', fontSize: '0.7rem' }}>Fermer</button>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '0.35rem' }}>
        {KEYBOARD_SYMBOLS.map((sym, i) => (
          <button
            key={i}
            onClick={() => onInsert(sym.latex)}
            className="btn btn-secondary"
            style={{ padding: '0.4rem', fontSize: '0.85rem', fontFamily: 'monospace' }}
            title={`Insérer ${sym.latex}`}
            aria-label={`Symbole mathématique ${sym.label}`}
          >
            {sym.label}
          </button>
        ))}
      </div>
    </div>
  );
}
