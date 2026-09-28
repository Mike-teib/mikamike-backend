import React, { useState } from 'react';
import { ChevronDown, ChevronUp, X } from 'lucide-react';

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
  { label: "f'(x)", latex: "f'(x)" },
  { label: '∑', latex: '\\sum' }
];

export default function MathKeyboard({ onInsert, onClose }) {
  const [expanded, setExpanded] = useState(false);
  const visibleSymbols = expanded ? KEYBOARD_SYMBOLS : KEYBOARD_SYMBOLS.slice(0, 8);

  return (
    <div className={`glass-card math-keyboard-dock ${expanded ? 'is-expanded' : 'is-compact'}`}>
      <div className="math-keyboard-head">
        <strong>Clavier maths</strong>
        <div className="math-keyboard-actions">
          <button
            type="button"
            onClick={() => setExpanded(value => !value)}
            className="btn btn-outline"
            aria-label={expanded ? 'Réduire le clavier mathématique' : 'Agrandir le clavier mathématique'}
          >
            {expanded ? <ChevronDown size={15} /> : <ChevronUp size={15} />}
            {expanded ? 'Réduire' : 'Plus'}
          </button>
          {onClose && (
            <button type="button" onClick={onClose} className="btn btn-outline" aria-label="Fermer le clavier mathématique">
              <X size={15} />
            </button>
          )}
        </div>
      </div>

      <div className="math-keyboard-grid" role="group" aria-label="Symboles mathématiques">
        {visibleSymbols.map((sym) => (
          <button
            key={sym.label}
            type="button"
            onClick={() => onInsert(sym.latex)}
            className="btn btn-secondary math-key"
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
