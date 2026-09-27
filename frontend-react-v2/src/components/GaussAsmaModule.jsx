import React, { useState } from 'react';
import katex from 'katex';
import { Fraction } from '../utils/Fraction';
import { Sparkles, HelpCircle, CheckCircle2, RotateCcw, Eye, ArrowRight, Layers } from 'lucide-react';

const SYSTEMS_LIST = [
  {
    id: 'P1A-N1-01',
    title: 'Niveau 1 — Exercice 1 (Trois 1 en diagonale)',
    statement: 'x + y + z = 6 \\\\ x + 2y + 3z = 14 \\\\ x + 4y + 9z = 36',
    initialMatrix: [
      [1, 1, 1, 6],
      [1, 2, 3, 14],
      [1, 4, 9, 36]
    ],
    targetSolution: 'x = 1, y = 2, z = 3',
    hints: [
      'Indice 1 : Élimine x en L2 avec L2 ← L2 - L1, puis en L3 avec L3 ← L3 - L1.',
      'Indice 2 : Une fois L2 = (0, 1, 2 | 8), élimine y en L3 avec L3 ← L3 - 3*L2.'
    ],
    stepsTargetCount: 3
  },
  {
    id: 'P1A-N1-02',
    title: 'Niveau 1 — Exercice 2 (Coefficients simples)',
    statement: 'x + 2y - z = 2 \\\\ 2x + 5y + z = 15 \\\\ 3x + 6y + 2z = 16',
    initialMatrix: [
      [1, 2, -1, 2],
      [2, 5, 1, 15],
      [3, 6, 2, 16]
    ],
    targetSolution: 'x = -6, y = 5, z = 2',
    hints: [
      'Indice 1 : Utilise L2 ← L2 - 2*L1 et L3 ← L3 - 3*L1.',
      'Indice 2 : Observe que L3 devient directement (0, 0, 5 | 10) sans étape supplémentaire !'
    ],
    stepsTargetCount: 2
  },
  {
    id: 'P1A-N2-02',
    title: 'Niveau 2 — Exercice 5 (Pivot Nul : Permutation de lignes)',
    statement: '0x + 2y + z = 5 \\\\ x + y + z = 6 \\\\ 3x - y + 2z = 7',
    initialMatrix: [
      [0, 2, 1, 5],
      [1, 1, 1, 6],
      [3, -1, 2, 7]
    ],
    targetSolution: 'x = 4, y = 3, z = -1',
    hints: [
      'Indice 1 : Le pivot a11 est nul ! Échange d’abord L1 et L2 avec L1 ↔ L2.',
      'Indice 2 : Après échange, élimine 3x en L3 avec L3 ← L3 - 3*L1.'
    ],
    stepsTargetCount: 4
  },
  {
    id: 'P1A-N3-01',
    title: 'Niveau 3 — Exercice 7 (Fractions rationnelles)',
    statement: '2x + 3y + z = 4 \\\\ 3x + 2y + 4z = 7 \\\\ x + 4y + 2z = 5',
    initialMatrix: [
      [2, 3, 1, 4],
      [3, 2, 4, 7],
      [1, 4, 2, 5]
    ],
    targetSolution: 'x = 3/5, y = 3/5, z = 1',
    hints: [
      'Indice 1 : Échange d’abord L1 et L3 avec L1 ↔ L3 pour travailler avec un pivot égal à 1 en (1,1).',
      'Indice 2 : Fais L2 ← L2 - 3*L1 et L3 ← L3 - 2*L1.'
    ],
    stepsTargetCount: 4
  }
];

function renderKaTeX(latex, display = false) {
  try {
    const html = katex.renderToString(latex, { displayMode: display, throwOnError: false });
    return <span dangerouslySetInnerHTML={{ __html: html }} />;
  } catch (e) {
    return <code>{latex}</code>;
  }
}

export default function GaussAsmaModule() {
  const [selectedSystemIndex, setSelectedSystemIndex] = useState(0);
  const activeSystem = SYSTEMS_LIST[selectedSystemIndex];

  const [matrix, setMatrix] = useState(() =>
    activeSystem.initialMatrix.map(row => row.map(v => new Fraction(v)))
  );

  const [stepHistory, setStepHistory] = useState([]);
  const [activeHintLevel, setActiveHintLevel] = useState(0);
  const [showFullCorrection, setShowFullCorrection] = useState(false);
  const [stepFeedback, setStepFeedback] = useState('');

  const [opType, setOpType] = useState('comb');
  const [targetRow, setTargetRow] = useState(2);
  const [sourceRow, setSourceRow] = useState(1);
  const [swapRow2, setSwapRow2] = useState(2);
  const [factorStr, setFactorStr] = useState('-1');

  const resetSystem = (index) => {
    const idx = index !== undefined ? index : selectedSystemIndex;
    setSelectedSystemIndex(idx);
    const sys = SYSTEMS_LIST[idx];
    setMatrix(sys.initialMatrix.map(row => row.map(v => new Fraction(v))));
    setStepHistory([]);
    setActiveHintLevel(0);
    setShowFullCorrection(false);
    setStepFeedback('Matrice réinitialisée. Prête pour une nouvelle étape !');
  };

  const handleExecuteOperation = (e) => {
    e?.preventDefault();
    try {
      const newMatrix = matrix.map(row => row.map(cell => new Fraction(cell.n, cell.d)));
      let opDescription = '';

      if (opType === 'swap') {
        const r1 = targetRow - 1;
        const r2 = swapRow2 - 1;
        if (r1 === r2) {
          setStepFeedback('Attention Asma : Échanger une ligne avec elle-même ne change rien !');
          return;
        }
        const temp = newMatrix[r1];
        newMatrix[r1] = newMatrix[r2];
        newMatrix[r2] = temp;
        opDescription = `Échange L${targetRow} ↔ L${swapRow2}`;
      } else if (opType === 'comb') {
        const rT = targetRow - 1;
        const rS = sourceRow - 1;
        if (rT === rS) {
          setStepFeedback('Attention Asma : Choisis deux lignes différentes pour la combinaison !');
          return;
        }
        const k = new Fraction(factorStr);
        for (let col = 0; col < 4; col++) {
          newMatrix[rT][col] = newMatrix[rT][col].add(newMatrix[rS][col].mul(k));
        }
        const kStr = k.toString();
        const signStr = k.n >= 0 ? `+ ${kStr}` : `- ${k.mul(-1).toString()}`;
        opDescription = `L${targetRow} ← L${targetRow} ${signStr} × L${sourceRow}`;
      } else if (opType === 'scale') {
        const rT = targetRow - 1;
        const k = new Fraction(factorStr);
        if (k.isZero()) {
          setStepFeedback('Erreur : Multiplier une ligne par 0 est interdit !');
          return;
        }
        for (let col = 0; col < 4; col++) {
          newMatrix[rT][col] = newMatrix[rT][col].mul(k);
        }
        opDescription = `L${targetRow} ← ${k.toString()} × L${targetRow}`;
      }

      setMatrix(newMatrix);
      setStepHistory(prev => [...prev, { desc: opDescription, matrix: newMatrix }]);
      setStepFeedback(`Bravo Asma ! Opération réussie : ${opDescription}`);
    } catch (err) {
      setStepFeedback(`Erreur de saisie : ${err.message}`);
    }
  };

  const isTriangular =
    matrix[1][0].isZero() && matrix[2][0].isZero() && matrix[2][1].isZero();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', padding: '1.25rem', color: '#f8fafc', maxWidth: '1100px', margin: '0 auto' }}>
      {/* Header Banner */}
      <div className="glass-card" style={{ padding: '1.25rem', background: 'linear-gradient(135deg, rgba(30,41,59,0.95), rgba(51,65,85,0.8))', border: '1px solid #3b82f6' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
              <Sparkles color="#60a5fa" size={24} />
              <h2 style={{ fontSize: '1.25rem', fontWeight: '800', color: '#60a5fa' }}>
                Révision Pivot de Gauss 3×3 — Module Spécial Asma
              </h2>
            </div>
            <p style={{ fontSize: '0.85rem', color: '#94a3b8' }}>
              Résolution pas-à-pas avec fractions exactes, indices pédagogiques et vérification d'étapes.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <select
              value={selectedSystemIndex}
              onChange={(e) => resetSystem(parseInt(e.target.value, 10))}
              className="selector-select"
              style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '8px', padding: '0.4rem 0.75rem' }}
              aria-label="Sélectionner l'exercice pour Asma"
            >
              {SYSTEMS_LIST.map((sys, idx) => (
                <option key={sys.id} value={idx}>{sys.title}</option>
              ))}
            </select>
            <button onClick={() => resetSystem()} className="btn btn-outline" aria-label="Recommencer cet exercice">
              <RotateCcw size={16} /> Recommencer
            </button>
          </div>
        </div>
      </div>

      {/* Main Grid: System Statement & Augmented Matrix Display */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.25rem' }}>
        {/* Left Card: Énoncé & Étapes effectuées */}
        <div className="glass-card" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: '700', color: '#38bdf8' }}>1. Énoncé du Système</h3>
          <div style={{ background: '#0f172a', padding: '1rem', borderRadius: '8px', border: '1px solid #334155', textAlign: 'center', fontSize: '1.05rem' }}>
            {renderKaTeX(`\\begin{cases} ${activeSystem.statement} \\end{cases}`, true)}
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: '700', color: '#94a3b8' }}>
              Compteur : <span style={{ color: '#34d399' }}>Étape {stepHistory.length}</span> / {activeSystem.stepsTargetCount} conseillées
            </span>
            {isTriangular && (
              <span className="badge-disponible" style={{ fontSize: '0.8rem' }}>
                <CheckCircle2 size={14} style={{ display: 'inline', marginRight: '4px' }} /> Forme Triangulaire Atteinte !
              </span>
            )}
          </div>

          {/* History of Operations */}
          {stepHistory.length > 0 && (
            <div style={{ background: '#090d16', padding: '0.75rem', borderRadius: '8px', border: '1px solid #334155' }}>
              <div style={{ fontSize: '0.8rem', fontWeight: '700', color: '#60a5fa', marginBottom: '0.35rem' }}>Historique de tes opérations :</div>
              <ol style={{ paddingLeft: '1.2rem', fontSize: '0.85rem', color: '#cbd5e1' }}>
                {stepHistory.map((h, i) => (
                  <li key={i} style={{ margin: '0.2rem 0' }}>{h.desc}</li>
                ))}
              </ol>
            </div>
          )}
        </div>

        {/* Right Card: Matrice Augmentée Actuelle */}
        <div className="glass-card" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem', alignItems: 'center' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: '700', color: '#fbbf24', alignSelf: 'flex-start' }}>
            2. Matrice Augmentée Actuelle (A|B)
          </h3>

          {/* Matrix Display Table with LaTeX brackets */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: '#0f172a', padding: '1.25rem', borderRadius: '12px', border: '1px solid #334155' }}>
            <div style={{ fontSize: '3rem', fontWeight: '300', color: '#64748b' }}>(</div>
            <table style={{ borderCollapse: 'collapse', textAlign: 'center' }}>
              <tbody>
                {matrix.map((row, rIdx) => (
                  <tr key={rIdx}>
                    <td style={{ padding: '0.2rem 0.5rem', fontSize: '0.8rem', color: '#94a3b8', fontWeight: '700' }}>L{rIdx + 1}</td>
                    {row.map((cell, cIdx) => (
                      <td
                        key={cIdx}
                        style={{
                          padding: '0.6rem 0.85rem',
                          minWidth: '55px',
                          borderRight: cIdx === 2 ? '2px solid #3b82f6' : 'none',
                          fontWeight: rIdx === cIdx ? '800' : '500',
                          color: cell.isZero() ? '#64748b' : (rIdx === cIdx ? '#38bdf8' : '#f8fafc'),
                          fontSize: '1.05rem'
                        }}
                      >
                        {renderKaTeX(cell.toKaTeX())}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            <div style={{ fontSize: '3rem', fontWeight: '300', color: '#64748b' }}>)</div>
          </div>

          {/* Live Feedback Banner */}
          {stepFeedback && (
            <div style={{ fontSize: '0.85rem', padding: '0.6rem 0.9rem', borderRadius: '8px', background: 'rgba(59, 130, 246, 0.15)', border: '1px solid rgba(59, 130, 246, 0.4)', color: '#60a5fa', width: '100%' }}>
              {stepFeedback}
            </div>
          )}
        </div>
      </div>

      {/* 3. Interactive Operation Selector */}
      <div className="glass-card" style={{ padding: '1.25rem', background: '#1e293b', border: '1px solid #3b82f6' }}>
        <h3 style={{ fontSize: '1.1rem', fontWeight: '800', color: '#38bdf8', marginBottom: '1rem' }}>
          3. Asma, quelle opération veux-tu faire ?
        </h3>

        <form onSubmit={handleExecuteOperation} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer', fontSize: '0.9rem' }}>
              <input type="radio" name="opType" value="comb" checked={opType === 'comb'} onChange={() => setOpType('comb')} />
              <span><strong>Combinaison</strong> (ex: $L_2 \\leftarrow L_2 + k L_1$)</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer', fontSize: '0.9rem' }}>
              <input type="radio" name="opType" value="swap" checked={opType === 'swap'} onChange={() => setOpType('swap')} />
              <span><strong>Échanger 2 lignes</strong> ($L_i \\leftrightarrow L_j$)</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer', fontSize: '0.9rem' }}>
              <input type="radio" name="opType" value="scale" checked={opType === 'scale'} onChange={() => setOpType('scale')} />
              <span><strong>Multiplier une ligne</strong> ($L_i \\leftarrow k L_i$)</span>
            </label>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap', background: '#0f172a', padding: '0.85rem', borderRadius: '8px', border: '1px solid #334155' }}>
            {opType === 'comb' && (
              <>
                <span style={{ fontWeight: '600' }}>Modifier</span>
                <select value={targetRow} onChange={(e) => setTargetRow(parseInt(e.target.value, 10))} className="selector-select" style={{ background: '#1e293b' }}>
                  <option value={1}>L1</option>
                  <option value={2}>L2</option>
                  <option value={3}>L3</option>
                </select>
                <span>← L{targetRow} +</span>
                <input
                  type="text"
                  value={factorStr}
                  onChange={(e) => setFactorStr(e.target.value)}
                  placeholder="ex: -2 ou 1/3"
                  style={{ width: '90px', background: '#1e293b', border: '1px solid #334155', color: '#fff', padding: '0.3rem 0.5rem', borderRadius: '6px', textAlign: 'center' }}
                />
                <span>×</span>
                <select value={sourceRow} onChange={(e) => setSourceRow(parseInt(e.target.value, 10))} className="selector-select" style={{ background: '#1e293b' }}>
                  <option value={1}>L1</option>
                  <option value={2}>L2</option>
                  <option value={3}>L3</option>
                </select>
              </>
            )}

            {opType === 'swap' && (
              <>
                <span style={{ fontWeight: '600' }}>Échanger</span>
                <select value={targetRow} onChange={(e) => setTargetRow(parseInt(e.target.value, 10))} className="selector-select" style={{ background: '#1e293b' }}>
                  <option value={1}>L1</option>
                  <option value={2}>L2</option>
                  <option value={3}>L3</option>
                </select>
                <span>↔</span>
                <select value={swapRow2} onChange={(e) => setSwapRow2(parseInt(e.target.value, 10))} className="selector-select" style={{ background: '#1e293b' }}>
                  <option value={1}>L1</option>
                  <option value={2}>L2</option>
                  <option value={3}>L3</option>
                </select>
              </>
            )}

            {opType === 'scale' && (
              <>
                <span style={{ fontWeight: '600' }}>Multiplier</span>
                <select value={targetRow} onChange={(e) => setTargetRow(parseInt(e.target.value, 10))} className="selector-select" style={{ background: '#1e293b' }}>
                  <option value={1}>L1</option>
                  <option value={2}>L2</option>
                  <option value={3}>L3</option>
                </select>
                <span>←</span>
                <input
                  type="text"
                  value={factorStr}
                  onChange={(e) => setFactorStr(e.target.value)}
                  placeholder="ex: -1/2 ou 3"
                  style={{ width: '90px', background: '#1e293b', border: '1px solid #334155', color: '#fff', padding: '0.3rem 0.5rem', borderRadius: '6px', textAlign: 'center' }}
                />
                <span>× L{targetRow}</span>
              </>
            )}

            <button type="submit" className="btn btn-primary" style={{ marginLeft: 'auto' }}>
              Appliquer l'opération
            </button>
          </div>
        </form>

        <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem', flexWrap: 'wrap' }}>
          <button
            onClick={() => setActiveHintLevel(1)}
            className={`btn ${activeHintLevel >= 1 ? 'btn-primary' : 'btn-secondary'}`}
            aria-label="Afficher Indice 1"
          >
            <HelpCircle size={16} /> Indice 1
          </button>

          <button
            onClick={() => setActiveHintLevel(2)}
            className={`btn ${activeHintLevel >= 2 ? 'btn-primary' : 'btn-secondary'}`}
            aria-label="Afficher Indice 2"
          >
            <HelpCircle size={16} /> Indice 2
          </button>

          <button
            onClick={() => {
              if (isTriangular) {
                setStepFeedback('Félicitations Asma ! Ta matrice est parfaitement triangulaire.');
              } else {
                setStepFeedback('Continue Asma : il reste des termes non nuls sous la diagonale principale.');
              }
            }}
            className="btn btn-outline"
          >
            <CheckCircle2 size={16} /> Vérifier mon étape
          </button>

          <button
            onClick={() => setShowFullCorrection(!showFullCorrection)}
            className="btn btn-outline"
            style={{ marginLeft: 'auto', color: '#fbbf24', borderColor: '#fbbf24' }}
          >
            <Eye size={16} /> {showFullCorrection ? 'Masquer la correction' : 'Voir la correction à la fin'}
          </button>
        </div>

        {activeHintLevel >= 1 && (
          <div style={{ marginTop: '0.75rem', padding: '0.75rem', background: 'rgba(245,158,11,0.15)', border: '1px solid rgba(245,158,11,0.4)', borderRadius: '8px', color: '#fbbf24', fontSize: '0.85rem' }}>
            <strong>Indice 1 : </strong> {renderKaTeX(activeSystem.hints[0])}
          </div>
        )}

        {activeHintLevel >= 2 && (
          <div style={{ marginTop: '0.5rem', padding: '0.75rem', background: 'rgba(245,158,11,0.2)', border: '1px solid rgba(245,158,11,0.5)', borderRadius: '8px', color: '#fbbf24', fontSize: '0.85rem' }}>
            <strong>Indice 2 : </strong> {renderKaTeX(activeSystem.hints[1])}
          </div>
        )}

        {showFullCorrection && (
          <div style={{ marginTop: '1rem', padding: '1rem', background: 'rgba(16,185,129,0.15)', border: '1px solid #10b981', borderRadius: '8px', color: '#34d399' }}>
            <h4 style={{ fontSize: '0.95rem', fontWeight: '800', marginBottom: '0.35rem' }}>Correction Complète Formelle</h4>
            <p style={{ fontSize: '0.9rem' }}>Solution unique attendue : <strong>{activeSystem.targetSolution}</strong></p>
          </div>
        )}
      </div>
    </div>
  );
}
