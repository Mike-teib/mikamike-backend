import React, { useState } from 'react';
import katex from 'katex';
import { Fraction } from '../utils/Fraction';
import {
  FileImage,
  RotateCw,
  ZoomIn,
  ZoomOut,
  Crop,
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  RotateCcw,
  Eye,
  Info,
  ShieldAlert,
  Sliders,
  Layers,
  Sparkles
} from 'lucide-react';

const PRESET_SYSTEMS = [
  {
    id: 'PHOTO_COURSE_ASMA',
    title: 'Photo de cours Asma (Extrait avec L3 à confirmer)',
    l1: 'x - 5y - 7z = 3',
    l2: '5x + 3y + 3z = 3',
    l3: '? x + 3y + 3z = 3',
    isUncertain: true,
    uncertainLine: 'L3',
    uncertainTerm: '? x',
    defaultMatrix: [
      [1, -5, -7, 3],
      [5, 3, 3, 3],
      [2, 3, 3, 3] // Default after confirmation
    ],
    hints: [
      'Indice 1 : Élimine d\'abord x en L2 via L2 ← L2 - 5*L1.',
      'Indice 2 : Élimine x en L3 via L3 ← L3 - 2*L1.'
    ],
    whyExplanation: 'Pourquoi cette étape ? Le pivot a11=1 est idéal en L1. On annule le coefficient 5 sous le pivot en L2 en retranchant 5*L1.'
  },
  {
    id: 'EX1_STANDARD',
    title: 'Système Standard 1 (Pivots 1 simples)',
    l1: 'x + y + z = 6',
    l2: 'x + 2y + 3z = 14',
    l3: 'x + 4y + 9z = 36',
    isUncertain: false,
    defaultMatrix: [
      [1, 1, 1, 6],
      [1, 2, 3, 14],
      [1, 4, 9, 36]
    ],
    hints: [
      'Indice 1 : Élimine x en L2 avec L2 ← L2 - L1, et en L3 avec L3 ← L3 - L1.',
      'Indice 2 : Une fois L2 = (0, 1, 2 | 8), fais L3 ← L3 - 3*L2.'
    ],
    whyExplanation: 'Pourquoi cette étape ? Le pivot a11=1 permet d\'annuler directement x dans L2 et L3 sans fraction.'
  },
  {
    id: 'EX5_ZERO_PIVOT',
    title: 'Système Standard 2 (Pivot Nul : Permutation requise)',
    l1: '0x + 2y + z = 5',
    l2: 'x + y + z = 6',
    l3: '3x - y + 2z = 7',
    isUncertain: false,
    defaultMatrix: [
      [0, 2, 1, 5],
      [1, 1, 1, 6],
      [3, -1, 2, 7]
    ],
    hints: [
      'Indice 1 : Le pivot a11 est nul ! Échange d’abord L1 et L2 avec L1 ↔ L2.',
      'Indice 2 : Après échange, élimine 3x en L3 avec L3 ← L3 - 3*L1.'
    ],
    whyExplanation: 'Pourquoi cette étape ? On ne peut pas diviser par 0. Échanger L1 et L2 fournit un pivot non nul a11=1.'
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

export default function CanonicalGaussIntegration() {
  const [selectedPresetIdx, setSelectedPresetIdx] = useState(0);
  const activePreset = PRESET_SYSTEMS[selectedPresetIdx];

  // Photo inspection state
  const [rotation, setRotation] = useState(0);
  const [zoom, setZoom] = useState(1);
  const [isCropping, setIsCropping] = useState(false);

  // Equation confirmation state
  const [equationsConfirmed, setEquationsConfirmed] = useState(!activePreset.isUncertain);
  const [confirmedL3Term, setConfirmedL3Term] = useState('2x');
  const [customL1, setCustomL1] = useState(activePreset.l1);
  const [customL2, setCustomL2] = useState(activePreset.l2);
  const [customL3, setCustomL3] = useState(activePreset.l3);

  // Gauss Matrix State (stored as 2D array of Fraction instances)
  const [matrix, setMatrix] = useState(() =>
    activePreset.defaultMatrix.map(row => row.map(v => new Fraction(v)))
  );
  const [stepHistory, setStepHistory] = useState([]);

  // Pedagogical Controls State
  const [activeHint, setActiveHint] = useState(0); // 0, 1, 2
  const [showWhy, setShowWhy] = useState(false);
  const [showFullCorrection, setShowFullCorrection] = useState(false);
  const [feedbackMsg, setFeedbackMsg] = useState('');

  // Row operation form state
  const [opType, setOpType] = useState('comb'); // 'comb' | 'swap' | 'scale'
  const [targetRow, setTargetRow] = useState(2);
  const [sourceRow, setSourceRow] = useState(1);
  const [swapRow2, setSwapRow2] = useState(2);
  const [factorStr, setFactorStr] = useState('-1');

  // Reset System & Matrix
  const handleSelectPreset = (idx) => {
    setSelectedPresetIdx(idx);
    const preset = PRESET_SYSTEMS[idx];
    setEquationsConfirmed(!preset.isUncertain);
    setCustomL1(preset.l1);
    setCustomL2(preset.l2);
    setCustomL3(preset.l3);
    setMatrix(preset.defaultMatrix.map(row => row.map(v => new Fraction(v))));
    setStepHistory([]);
    setActiveHint(0);
    setShowWhy(false);
    setShowFullCorrection(false);
    setFeedbackMsg(preset.isUncertain ? '⚠️ Image partielle : confirme la ligne L3 pour déverrouiller le solveur.' : 'Système chargé et déverrouillé.');
  };

  const handleConfirmEquations = (e) => {
    e?.preventDefault();
    setEquationsConfirmed(true);
    setCustomL3(prev => prev.replace('? x', confirmedL3Term));
    setFeedbackMsg('Équations confirmées par Asma ! Le moteur du pivot de Gauss est déverrouillé.');
  };

  const handleExecuteOperation = (e) => {
    e?.preventDefault();
    if (!equationsConfirmed) {
      setFeedbackMsg('🔒 Moteur bloqué : tu dois d\'abord confirmer les équations de l\'image avant d\'exécuter des opérations !');
      return;
    }

    try {
      const newMatrix = matrix.map(row => row.map(cell => new Fraction(cell.n, cell.d)));
      let opDesc = '';

      if (opType === 'swap') {
        const r1 = targetRow - 1;
        const r2 = swapRow2 - 1;
        if (r1 === r2) {
          setFeedbackMsg('Attention Asma : Échanger une ligne avec elle-même ne change rien !');
          return;
        }
        const temp = newMatrix[r1];
        newMatrix[r1] = newMatrix[r2];
        newMatrix[r2] = temp;
        opDesc = `Échange L${targetRow} ↔ L${swapRow2}`;
      } else if (opType === 'comb') {
        const rT = targetRow - 1;
        const rS = sourceRow - 1;
        if (rT === rS) {
          setFeedbackMsg('Attention Asma : Choisis deux lignes différentes pour la combinaison !');
          return;
        }
        const k = new Fraction(factorStr);
        for (let col = 0; col < 4; col++) {
          newMatrix[rT][col] = newMatrix[rT][col].add(newMatrix[rS][col].mul(k));
        }
        const kStr = k.toString();
        const signStr = k.n >= 0 ? `+ ${kStr}` : `- ${k.mul(-1).toString()}`;
        opDesc = `L${targetRow} ← L${targetRow} ${signStr} × L${sourceRow}`;
      } else if (opType === 'scale') {
        const rT = targetRow - 1;
        const k = new Fraction(factorStr);
        if (k.isZero()) {
          setFeedbackMsg('Erreur : Multiplier une ligne par 0 est interdit !');
          return;
        }
        for (let col = 0; col < 4; col++) {
          newMatrix[rT][col] = newMatrix[rT][col].mul(k);
        }
        opDesc = `L${targetRow} ← ${k.toString()} × L${targetRow}`;
      }

      setMatrix(newMatrix);
      setStepHistory(prev => [...prev, { desc: opDesc, matrix: newMatrix }]);
      setFeedbackMsg(`Bravo Asma ! Opération appliquée : ${opDesc}`);
    } catch (err) {
      setFeedbackMsg(`Erreur dans la saisie de la fraction : ${err.message}`);
    }
  };

  const isTriangular =
    matrix[1][0].isZero() && matrix[2][0].isZero() && matrix[2][1].isZero();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', padding: '1rem', color: '#f8fafc', maxWidth: '1200px', margin: '0 auto', width: '100%' }}>
      {/* 1. Header & Presets Switcher */}
      <div className="glass-card" style={{ padding: '1.25rem', background: 'linear-gradient(135deg, rgba(15,23,42,0.95), rgba(30,41,59,0.85))', border: '1px solid #3b82f6' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
              <Sparkles color="#60a5fa" size={24} />
              <h2 style={{ fontSize: '1.25rem', fontWeight: '800', color: '#60a5fa' }}>
                Outils › Pivot de Gauss 3×3 — Interface Canonique Asma
              </h2>
            </div>
            <p style={{ fontSize: '0.85rem', color: '#94a3b8' }}>
              Inspection d'image, levée des incertitudes, matrice 3x4 en fractions exactes et solveur pas-à-pas.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <select
              value={selectedPresetIdx}
              onChange={(e) => handleSelectPreset(parseInt(e.target.value, 10))}
              className="selector-select"
              style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '8px', padding: '0.45rem 0.75rem' }}
              aria-label="Sélectionner le mode d'entrée du système"
            >
              {PRESET_SYSTEMS.map((sys, idx) => (
                <option key={sys.id} value={idx}>{sys.title}</option>
              ))}
            </select>
            <button onClick={() => handleSelectPreset(selectedPresetIdx)} className="btn btn-outline" aria-label="Recommencer cet exercice">
              <RotateCcw size={16} /> Recommencer
            </button>
          </div>
        </div>
      </div>

      {/* 2. Top Row: IMAGE ORIGINALE vs CE QUE MIKA A COMPRIS */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '1.25rem' }}>
        {/* Left Column: Image Originale & Inspection Tools */}
        <div className="glass-card" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ fontSize: '0.95rem', fontWeight: '700', color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <FileImage size={18} /> IMAGE ORIGINALE
            </h3>
            <div style={{ display: 'flex', gap: '0.25rem' }}>
              <button onClick={() => setRotation(r => (r + 90) % 360)} className="btn btn-outline" style={{ padding: '3px 7px', fontSize: '0.75rem' }} title="Pivoter de 90°">
                <RotateCw size={13} /> Rotation
              </button>
              <button onClick={() => setZoom(z => Math.min(z + 0.2, 2.0))} className="btn btn-outline" style={{ padding: '3px 7px', fontSize: '0.75rem' }} title="Zoomer">
                <ZoomIn size={13} />
              </button>
              <button onClick={() => setZoom(z => Math.max(z - 0.2, 0.8))} className="btn btn-outline" style={{ padding: '3px 7px', fontSize: '0.75rem' }} title="Dézoomer">
                <ZoomOut size={13} />
              </button>
              <button onClick={() => setIsCropping(!isCropping)} className={`btn ${isCropping ? 'btn-primary' : 'btn-outline'}`} style={{ padding: '3px 7px', fontSize: '0.75rem' }} title="Mode Recadrage">
                <Crop size={13} /> Crop
              </button>
            </div>
          </div>

          {/* Photo Viewport Container */}
          <div style={{
            background: '#090d16',
            borderRadius: '8px',
            border: isCropping ? '2px dashed #3b82f6' : '1px solid #334155',
            padding: '1.25rem',
            minHeight: '200px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            overflow: 'hidden',
            position: 'relative'
          }}>
            <div style={{
              transform: `rotate(${rotation}deg) scale(${zoom})`,
              transition: 'transform 0.3s ease',
              textAlign: 'center',
              fontFamily: 'monospace',
              color: '#f8fafc',
              background: 'rgba(30, 41, 59, 0.95)',
              padding: '1rem 1.25rem',
              borderRadius: '8px',
              border: '1px solid #475569',
              boxShadow: '0 4px 16px rgba(0,0,0,0.5)',
              maxWidth: '95%'
            }}>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', marginBottom: '0.4rem' }}>
                📷 Photo utilisateur originale : PIVOT DE GAUSS
              </div>
              <div style={{ fontSize: '1rem', marginBottom: '0.2rem' }}>L1 : {activePreset.l1}</div>
              <div style={{ fontSize: '1rem', marginBottom: '0.2rem' }}>L2 : {activePreset.l2}</div>
              <div style={{ fontSize: '1rem', color: activePreset.isUncertain ? '#fbbf24' : '#f8fafc', background: activePreset.isUncertain ? 'rgba(245,158,11,0.2)' : 'transparent', padding: '2px 4px', borderRadius: '4px' }}>
                L3 : {activePreset.isUncertain ? <span style={{ textDecoration: 'wavy underline red' }}>[Masqué/Ombre]</span> : ''} {activePreset.l3.replace('? x', '')}
              </div>
            </div>
          </div>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8', textAlign: 'center' }}>
            Rotation: {rotation}° | Zoom: {Math.round(zoom * 100)}% {isCropping ? '| Mode Crop Actif' : ''}
          </div>
        </div>

        {/* Right Column: CE QUE MIKA A COMPRIS & CONFIRMER LES ÉQUATIONS */}
        <div className="glass-card" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
          <h3 style={{ fontSize: '0.95rem', fontWeight: '700', color: '#34d399', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Sparkles size={18} /> CE QUE MIKA A COMPRIS
          </h3>

          <div style={{ background: '#0f172a', padding: '0.85rem', borderRadius: '8px', border: '1px solid #334155', display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.875rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #1e293b', paddingBottom: '0.35rem' }}>
              <span>Ligne 1 ($L_1$) : {renderKaTeX(customL1)}</span>
              <span className="badge-disponible">Certain</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #1e293b', paddingBottom: '0.35rem' }}>
              <span>Ligne 2 ($L_2$) : {renderKaTeX(customL2)}</span>
              <span className="badge-disponible">Certain</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: !equationsConfirmed ? 'rgba(244, 63, 94, 0.1)' : 'rgba(16, 185, 129, 0.1)', padding: '0.4rem 0.6rem', borderRadius: '6px' }}>
              <span>Ligne 3 ($L_3$) : {renderKaTeX(customL3)}</span>
              {!equationsConfirmed ? (
                <span className="badge-preparation" style={{ background: 'rgba(244, 63, 94, 0.3)', color: '#fda4af', border: '1px solid #f43f5e' }}>
                  <ShieldAlert size={12} style={{ display: 'inline', marginRight: '3px' }} /> A CONFIRMER
                </span>
              ) : (
                <span className="badge-disponible">Confirmé par Asma</span>
              )}
            </div>
          </div>

          {/* Formulaire de Confirmation d'Équations */}
          {!equationsConfirmed ? (
            <div style={{ background: 'rgba(245, 158, 11, 0.15)', border: '1px solid #f59e0b', borderRadius: '8px', padding: '0.85rem', display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#fbbf24', fontWeight: '700', fontSize: '0.85rem' }}>
                <AlertTriangle size={18} />
                <span>CONFIRMER LES ÉQUATIONS — Interdiction d'inventer</span>
              </div>
              <p style={{ fontSize: '0.8rem', color: '#cbd5e1', lineHeight: '1.35' }}>
                Je lis correctement <strong>L1</strong> et <strong>L2</strong>, mais une partie de <strong>L3</strong> est masquée. Peux-tu me confirmer le premier terme devant $x$ dans $L_3$ ?
              </p>

              <form onSubmit={handleConfirmEquations} style={{ display: 'flex', gap: '0.5rem' }}>
                <input
                  type="text"
                  value={confirmedL3Term}
                  onChange={(e) => setConfirmedL3Term(e.target.value)}
                  placeholder="ex: 2x ou -x"
                  style={{ flex: 1, background: '#0f172a', border: '1px solid #334155', color: '#fff', padding: '0.4rem 0.65rem', borderRadius: '6px', fontSize: '0.85rem' }}
                />
                <button type="submit" className="btn btn-primary" style={{ padding: '0.4rem 0.85rem', fontSize: '0.85rem' }}>
                  Confirmer L3
                </button>
              </form>
            </div>
          ) : (
            <div style={{ background: 'rgba(16, 185, 129, 0.12)', border: '1px solid #10b981', borderRadius: '8px', padding: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#34d399', fontSize: '0.85rem' }}>
              <CheckCircle2 size={18} />
              <div>
                <strong>Équations confirmées !</strong> Le système 3x3 est complètement déverrouillé.
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 3. Bottom Section: MATRICE 3x4 AUGMENTÉE & ÉTAPE ACTUELLE */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.25rem' }}>
        {/* Left Column: Étape Actuelle & Historique */}
        <div className="glass-card" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ fontSize: '0.95rem', fontWeight: '700', color: '#38bdf8' }}>ÉTAPE ACTUELLE</h3>
            <span style={{ fontSize: '0.8rem', fontWeight: '700', color: '#94a3b8' }}>
              Compteur : <span style={{ color: '#34d399' }}>Étape {stepHistory.length}</span>
            </span>
          </div>

          {stepHistory.length === 0 ? (
            <div style={{ fontSize: '0.85rem', color: '#94a3b8', fontStyle: 'italic', background: '#0f172a', padding: '0.75rem', borderRadius: '6px' }}>
              Aucune opération appliquée. Applique une première combinaison ou permutation ci-contre.
            </div>
          ) : (
            <div style={{ background: '#090d16', padding: '0.75rem', borderRadius: '8px', border: '1px solid #334155' }}>
              <div style={{ fontSize: '0.8rem', fontWeight: '700', color: '#60a5fa', marginBottom: '0.35rem' }}>Historique des opérations effectuées :</div>
              <ol style={{ paddingLeft: '1.2rem', fontSize: '0.85rem', color: '#cbd5e1' }}>
                {stepHistory.map((h, i) => (
                  <li key={i} style={{ margin: '0.2rem 0' }}>{h.desc}</li>
                ))}
              </ol>
            </div>
          )}

          {isTriangular && (
            <div style={{ background: 'rgba(16, 185, 129, 0.15)', border: '1px solid #10b981', borderRadius: '8px', padding: '0.75rem', color: '#34d399', fontSize: '0.85rem', fontWeight: '600' }}>
              <CheckCircle2 size={16} style={{ display: 'inline', marginRight: '4px' }} /> Forme Triangulaire Supérieure atteinte avec succès !
            </div>
          )}

          {/* Live Feedback Banner */}
          {feedbackMsg && (
            <div style={{ fontSize: '0.85rem', padding: '0.6rem 0.85rem', borderRadius: '8px', background: 'rgba(59, 130, 246, 0.15)', border: '1px solid rgba(59, 130, 246, 0.4)', color: '#60a5fa' }}>
              {feedbackMsg}
            </div>
          )}
        </div>

        {/* Right Column: Matrice 3x4 Display Container (Never cut on mobile) */}
        <div className="glass-card" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.85rem', alignItems: 'center' }}>
          <h3 style={{ fontSize: '0.95rem', fontWeight: '700', color: '#fbbf24', alignSelf: 'flex-start' }}>
            MATRICE 3×4 AUGMENTÉE (A|B)
          </h3>

          {/* Mobile responsive container with horizontal overflow auto */}
          <div style={{ width: '100%', overflowX: 'auto', display: 'flex', justifyContent: 'center', padding: '0.5rem 0' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', background: '#0f172a', padding: '1rem 1.25rem', borderRadius: '12px', border: '1px solid #334155', minWidth: '280px' }}>
              <div style={{ fontSize: '2.8rem', fontWeight: '300', color: '#64748b' }}>(</div>
              <table style={{ borderCollapse: 'collapse', textAlign: 'center', margin: '0 auto' }}>
                <tbody>
                  {matrix.map((row, rIdx) => (
                    <tr key={rIdx}>
                      <td style={{ padding: '0.2rem 0.4rem', fontSize: '0.75rem', color: '#94a3b8', fontWeight: '700' }}>L{rIdx + 1}</td>
                      {row.map((cell, cIdx) => (
                        <td
                          key={cIdx}
                          style={{
                            padding: '0.5rem 0.75rem',
                            minWidth: '50px',
                            borderRight: cIdx === 2 ? '2px solid #3b82f6' : 'none',
                            fontWeight: rIdx === cIdx ? '800' : '500',
                            color: cell.isZero() ? '#64748b' : (rIdx === cIdx ? '#38bdf8' : '#f8fafc'),
                            fontSize: '1rem'
                          }}
                        >
                          {renderKaTeX(cell.toKaTeX())}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              <div style={{ fontSize: '2.8rem', fontWeight: '300', color: '#64748b' }}>)</div>
            </div>
          </div>
        </div>
      </div>

      {/* 4. Panneau d'Opérations sur les lignes & Boutons Pédagogiques */}
      <div className="glass-card" style={{ padding: '1.25rem', background: '#1e293b', border: '1px solid #3b82f6' }}>
        <h3 style={{ fontSize: '1rem', fontWeight: '800', color: '#38bdf8', marginBottom: '0.85rem' }}>
          Asma, quelle opération veux-tu faire ?
        </h3>

        <form onSubmit={handleExecuteOperation} style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
          {/* Operation Selector Radios */}
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', fontSize: '0.875rem' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', cursor: 'pointer' }}>
              <input type="radio" name="canonOpType" value="comb" checked={opType === 'comb'} onChange={() => setOpType('comb')} disabled={!equationsConfirmed} />
              <span><strong>Combinaison</strong> ($L_i \\leftarrow L_i + k L_j$)</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', cursor: 'pointer' }}>
              <input type="radio" name="canonOpType" value="swap" checked={opType === 'swap'} onChange={() => setOpType('swap')} disabled={!equationsConfirmed} />
              <span><strong>Échanger 2 lignes</strong> ($L_i \\leftrightarrow L_j$)</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', cursor: 'pointer' }}>
              <input type="radio" name="canonOpType" value="scale" checked={opType === 'scale'} onChange={() => setOpType('scale')} disabled={!equationsConfirmed} />
              <span><strong>Multiplier une ligne</strong> ($L_i \\leftarrow k L_i$)</span>
            </label>
          </div>

          {/* Operation Inputs */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', flexWrap: 'wrap', background: '#0f172a', padding: '0.75rem 1rem', borderRadius: '8px', border: '1px solid #334155' }}>
            {opType === 'comb' && (
              <>
                <span style={{ fontWeight: '600', fontSize: '0.85rem' }}>Modifier</span>
                <select value={targetRow} onChange={(e) => setTargetRow(parseInt(e.target.value, 10))} className="selector-select" style={{ background: '#1e293b' }} disabled={!equationsConfirmed}>
                  <option value={1}>L1</option>
                  <option value={2}>L2</option>
                  <option value={3}>L3</option>
                </select>
                <span style={{ fontSize: '0.85rem' }}>← L{targetRow} +</span>
                <input
                  type="text"
                  value={factorStr}
                  onChange={(e) => setFactorStr(e.target.value)}
                  placeholder="ex: -2 ou 1/3"
                  style={{ width: '85px', background: '#1e293b', border: '1px solid #334155', color: '#fff', padding: '0.3rem 0.5rem', borderRadius: '6px', textAlign: 'center', fontSize: '0.85rem' }}
                  disabled={!equationsConfirmed}
                />
                <span style={{ fontSize: '0.85rem' }}>×</span>
                <select value={sourceRow} onChange={(e) => setSourceRow(parseInt(e.target.value, 10))} className="selector-select" style={{ background: '#1e293b' }} disabled={!equationsConfirmed}>
                  <option value={1}>L1</option>
                  <option value={2}>L2</option>
                  <option value={3}>L3</option>
                </select>
              </>
            )}

            {opType === 'swap' && (
              <>
                <span style={{ fontWeight: '600', fontSize: '0.85rem' }}>Échanger</span>
                <select value={targetRow} onChange={(e) => setTargetRow(parseInt(e.target.value, 10))} className="selector-select" style={{ background: '#1e293b' }} disabled={!equationsConfirmed}>
                  <option value={1}>L1</option>
                  <option value={2}>L2</option>
                  <option value={3}>L3</option>
                </select>
                <span style={{ fontSize: '0.85rem' }}>↔</span>
                <select value={swapRow2} onChange={(e) => setSwapRow2(parseInt(e.target.value, 10))} className="selector-select" style={{ background: '#1e293b' }} disabled={!equationsConfirmed}>
                  <option value={1}>L1</option>
                  <option value={2}>L2</option>
                  <option value={3}>L3</option>
                </select>
              </>
            )}

            {opType === 'scale' && (
              <>
                <span style={{ fontWeight: '600', fontSize: '0.85rem' }}>Multiplier</span>
                <select value={targetRow} onChange={(e) => setTargetRow(parseInt(e.target.value, 10))} className="selector-select" style={{ background: '#1e293b' }} disabled={!equationsConfirmed}>
                  <option value={1}>L1</option>
                  <option value={2}>L2</option>
                  <option value={3}>L3</option>
                </select>
                <span style={{ fontSize: '0.85rem' }}>←</span>
                <input
                  type="text"
                  value={factorStr}
                  onChange={(e) => setFactorStr(e.target.value)}
                  placeholder="ex: -1/2 ou 3"
                  style={{ width: '85px', background: '#1e293b', border: '1px solid #334155', color: '#fff', padding: '0.3rem 0.5rem', borderRadius: '6px', textAlign: 'center', fontSize: '0.85rem' }}
                  disabled={!equationsConfirmed}
                />
                <span style={{ fontSize: '0.85rem' }}>× L{targetRow}</span>
              </>
            )}

            <button type="submit" className="btn btn-primary" style={{ marginLeft: 'auto' }} disabled={!equationsConfirmed}>
              Appliquer l'opération
            </button>
          </div>
        </form>

        {/* Boutons Pédagogiques Mandatés */}
        <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem', flexWrap: 'wrap' }}>
          <button
            onClick={() => {
              if (isTriangular) {
                setFeedbackMsg('Félicitations Asma ! Ta matrice est parfaitement triangulaire.');
              } else {
                setFeedbackMsg('Continue Asma : il reste des termes non nuls sous la diagonale principale.');
              }
            }}
            className="btn btn-outline"
            disabled={!equationsConfirmed}
          >
            <CheckCircle2 size={15} /> Vérifier
          </button>

          <button
            onClick={() => setActiveHint(1)}
            className={`btn ${activeHint >= 1 ? 'btn-primary' : 'btn-secondary'}`}
            disabled={!equationsConfirmed}
          >
            <HelpCircle size={15} /> Indice 1
          </button>

          <button
            onClick={() => setActiveHint(2)}
            className={`btn ${activeHint >= 2 ? 'btn-primary' : 'btn-secondary'}`}
            disabled={!equationsConfirmed}
          >
            <HelpCircle size={15} /> Indice 2
          </button>

          <button
            onClick={() => setShowWhy(!showWhy)}
            className={`btn ${showWhy ? 'btn-primary' : 'btn-secondary'}`}
            disabled={!equationsConfirmed}
          >
            <Info size={15} /> Pourquoi ?
          </button>

          <button
            onClick={() => handleSelectPreset(selectedPresetIdx)}
            className="btn btn-outline"
          >
            <RotateCcw size={15} /> Recommencer
          </button>

          <button
            onClick={() => setShowFullCorrection(!showFullCorrection)}
            className="btn btn-outline"
            style={{ marginLeft: 'auto', color: '#fbbf24', borderColor: '#fbbf24' }}
            disabled={!equationsConfirmed}
          >
            <Eye size={15} /> {showFullCorrection ? 'Masquer la correction' : 'Voir la correction complète'}
          </button>
        </div>

        {/* Drawers pour Indices, Pourquoi, et Correction */}
        {activeHint >= 1 && (
          <div style={{ marginTop: '0.75rem', padding: '0.75rem', background: 'rgba(245,158,11,0.15)', border: '1px solid rgba(245,158,11,0.4)', borderRadius: '8px', color: '#fbbf24', fontSize: '0.85rem' }}>
            <strong>Indice 1 : </strong> {renderKaTeX(activePreset.hints[0])}
          </div>
        )}

        {activeHint >= 2 && (
          <div style={{ marginTop: '0.5rem', padding: '0.75rem', background: 'rgba(245,158,11,0.2)', border: '1px solid rgba(245,158,11,0.5)', borderRadius: '8px', color: '#fbbf24', fontSize: '0.85rem' }}>
            <strong>Indice 2 : </strong> {renderKaTeX(activePreset.hints[1])}
          </div>
        )}

        {showWhy && (
          <div style={{ marginTop: '0.75rem', padding: '0.75rem', background: 'rgba(59,130,246,0.15)', border: '1px solid #3b82f6', borderRadius: '8px', color: '#60a5fa', fontSize: '0.85rem' }}>
            <strong>Pourquoi cette étape ? </strong> {activePreset.whyExplanation}
          </div>
        )}

        {showFullCorrection && (
          <div style={{ marginTop: '0.85rem', padding: '0.85rem', background: 'rgba(16,185,129,0.15)', border: '1px solid #10b981', borderRadius: '8px', color: '#34d399', fontSize: '0.875rem' }}>
            <h4 style={{ fontWeight: '800', marginBottom: '0.35rem' }}>Correction Complète Masquée par Défaut (Révélée à la demande)</h4>
            <p>Forme triangulaire visée $\implies$ résolution par substitution arrière.</p>
          </div>
        )}
      </div>
    </div>
  );
}
