import React, { useState } from 'react';
import katex from 'katex';
import { CheckCircle, AlertTriangle, HelpCircle, ArrowRight, ArrowLeft } from 'lucide-react';

export const MOCK_EXERCISES = {
  'P1A1-006': {
    id: 'P1A1-006',
    chapter: 'P1A1 — Second degré',
    title: 'Résolution d\'équation du second degré avec discriminant',
    statement: 'On considère la fonction polynôme $f(x) = 2x^2 - 4x - 6$. Déterminer le discriminant $\\Delta$ et trouver les deux racines réelles $x_1$ et $x_2$.',
    latexFormula: 'f(x) = 2x^2 - 4x - 6',
    question: 'Quelle est la valeur du discriminant $\\Delta$ ?',
    correctAnswer: '64',
    hint: 'Formule du discriminant : $\\Delta = b^2 - 4ac$ avec $a=2$, $b=-4$, $c=-6$.',
    stepCorrection: '$\\Delta = (-4)^2 - 4 \\times 2 \\times (-6) = 16 + 48 = 64$. Comme $\\Delta > 0$, les racines sont $x_1 = \\frac{4 - 8}{4} = -1$ et $x_2 = \\frac{4 + 8}{4} = 3$.'
  },
  'P1A2-001': {
    id: 'P1A2-001',
    chapter: 'P1A2 — Dérivation',
    title: 'Nombre dérivé et taux de variation',
    statement: 'Soit $f(x) = x^2 + 3x$. Calculer le nombre dérivé $f\'(2)$ en utilisant la définition du taux de variation ou les formules usuelles.',
    latexFormula: 'f(x) = x^2 + 3x \\implies f\'(x) = 2x + 3',
    question: 'Quelle est la valeur de $f\'(2)$ ?',
    correctAnswer: '7',
    hint: 'Calcule $f\'(x) = 2x + 3$, puis remplace $x$ par 2.',
    stepCorrection: '$f\'(x) = 2x + 3$. Donc $f\'(2) = 2(2) + 3 = 7$.'
  },
  'P1A2-004': {
    id: 'P1A2-004',
    chapter: 'P1A2 — Dérivation',
    title: 'Dérivée d\'un polynôme de degré 3',
    statement: 'Soit $g(x) = x^3 - 6x^2 + 9x + 5$. Déterminer l\'expression de la fonction dérivée $g\'(x)$.',
    latexFormula: 'g(x) = x^3 - 6x^2 + 9x + 5',
    question: 'Que vaut le coefficient de $x$ dans $g\'(x) = 3x^2 + k x + 9$ ?',
    correctAnswer: '-12',
    hint: 'La dérivée de $-6x^2$ est $-6 \\times 2x = -12x$.',
    stepCorrection: '$g\'(x) = 3x^2 - 12x + 9$.'
  },
  'P1A2-005': {
    id: 'P1A2-005',
    chapter: 'P1A2 — Dérivation',
    title: 'Équation de la tangente à une courbe',
    statement: 'Déterminer l\'équation réduite de la tangente $(T)$ à la courbe $y = f(x)$ au point d\'abscisse $a = 1$, sachant que $f(1) = 4$ et $f\'(1) = 5$.',
    latexFormula: 'y = f\'(a)(x - a) + f(a)',
    question: 'Quelle est l\'ordonnée à l\'origine de la tangente $(T) : y = 5x + b$ ?',
    correctAnswer: '-1',
    hint: 'Remplace dans $y = 5(x - 1) + 4 = 5x - 5 + 4 = 5x - 1$.',
    stepCorrection: '$y = 5(x - 1) + 4 = 5x - 1$. Donc $b = -1$.'
  },
  'P1A2-006': {
    id: 'P1A2-006',
    chapter: 'P1A2 — Dérivation',
    title: 'Étude de signe de la dérivée et variations',
    statement: 'Soit $h\'(x) = 3(x - 1)(x - 3)$. Pour quelles valeurs de $x$ la fonction $h$ est-elle strictement croissante ?',
    latexFormula: 'h\'(x) > 0 \\iff x \\in ]-\\infty, 1[ \\cup ]3, +\\infty[',
    question: 'Combien d\'extrémums locaux la fonction $h$ possède-t-elle ?',
    correctAnswer: '2',
    hint: 'Le signe de $h\'(x)$ s\'annule et change de signe en $x = 1$ et $x = 3$.',
    stepCorrection: '$h\'(x)$ s\'annule en $x=1$ (maximum local) et $x=3$ (minimum local). La fonction possède 2 extrémums.'
  },
  'P1A2-007': {
    id: 'P1A2-007',
    chapter: 'P1A2 — Dérivation',
    title: 'Problème d\'optimisation géométrique',
    statement: 'On veut fabriquer une boîte rectangulaire sans couvercle de volume maximal à partir d\'une feuille carrée. Le volume est donné par $V(x) = 4x^3 - 40x^2 + 100x$.',
    latexFormula: 'V\'(x) = 12x^2 - 80x + 100',
    question: 'Quelle est la valeur exacte de $x$ qui maximise le volume $V(x)$ sur $]0, 5[$ ?',
    correctAnswer: '5/3',
    hint: 'Résous $V\'(x) = 0 \\implies 3x^2 - 20x + 25 = 0$. La racine valide est $x = 5/3$.',
    stepCorrection: '$V\'(x) = 0 \\implies (3x - 5)(x - 5) = 0$. Sur $]0, 5[$, la seule racine est $x = 5/3$.'
  },
  'P1A2-008': {
    id: 'P1A2-008',
    chapter: 'P1A2 — Dérivation',
    title: 'Vitesse instantanée et cinématique',
    statement: 'La position d\'un mobile sur un axe est $s(t) = -5t^2 + 20t + 2$ (en mètres, $t$ en secondes). Déterminer la vitesse instantanée $v(t) = s\'(t)$ à l\'instant $t = 2$ s.',
    latexFormula: 'v(t) = s\'(t) = -10t + 20',
    question: 'Quelle est la vitesse du mobile à $t = 2$ secondes (en m/s) ?',
    correctAnswer: '0',
    hint: 'Calcule $v(2) = -10(2) + 20$.',
    stepCorrection: '$v(2) = -10(2) + 20 = 0 \\text{ m/s}$. Le mobile s\'arrête à cet instant avant de changer de sens.'
  }
};

function renderKaTeX(text) {
  if (!text) return null;
  const parts = text.split(/(\$.*?\$)/g);
  return parts.map((part, index) => {
    if (part.startsWith('$') && part.endsWith('$')) {
      const math = part.slice(1, -1);
      try {
        const html = katex.renderToString(math, { throwOnError: false });
        return <span key={index} dangerouslySetInnerHTML={{ __html: html }} />;
      } catch (e) {
        return <code key={index}>{part}</code>;
      }
    }
    return <span key={index}>{part}</span>;
  });
}

export default function ExerciseViewer({ selectedExerciseId, onExerciseChange }) {
  const exerciseKeys = Object.keys(MOCK_EXERCISES);
  const currentKey = selectedExerciseId || exerciseKeys[0];
  const ex = MOCK_EXERCISES[currentKey] || MOCK_EXERCISES['P1A1-006'];

  const [userAnswer, setUserAnswer] = useState('');
  const [showHint, setShowHint] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [isCorrect, setIsCorrect] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    setSubmitted(true);
    if (userAnswer.trim() === ex.correctAnswer) {
      setIsCorrect(true);
    } else {
      setIsCorrect(false);
    }
  };

  const handleSelectNext = () => {
    const currentIndex = exerciseKeys.indexOf(currentKey);
    if (currentIndex < exerciseKeys.length - 1) {
      const nextKey = exerciseKeys[currentIndex + 1];
      onExerciseChange(nextKey);
      setUserAnswer('');
      setShowHint(false);
      setSubmitted(false);
    }
  };

  const handleSelectPrev = () => {
    const currentIndex = exerciseKeys.indexOf(currentKey);
    if (currentIndex > 0) {
      const prevKey = exerciseKeys[currentIndex - 1];
      onExerciseChange(prevKey);
      setUserAnswer('');
      setShowHint(false);
      setSubmitted(false);
    }
  };

  return (
    <div className="glass-card" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem', height: '100%', overflowY: 'auto' }}>
      {/* Exercise Navigation Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid #334155', paddingBottom: '0.75rem', flexWrap: 'wrap', gap: '0.5rem' }}>
        <div>
          <span style={{ fontSize: '0.75rem', fontWeight: '700', color: '#60a5fa', textTransform: 'uppercase' }}>
            {ex.chapter}
          </span>
          <h2 style={{ fontSize: '1.1rem', fontWeight: '700' }}>Exercice {ex.id}</h2>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <select
            value={currentKey}
            onChange={(e) => {
              onExerciseChange(e.target.value);
              setUserAnswer('');
              setShowHint(false);
              setSubmitted(false);
            }}
            className="selector-select"
            style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '6px' }}
            aria-label="Sélectionner l'exercice"
          >
            {exerciseKeys.map(k => (
              <option key={k} value={k}>{k} — {MOCK_EXERCISES[k].title}</option>
            ))}
          </select>
          <button onClick={handleSelectPrev} className="btn btn-outline" disabled={exerciseKeys.indexOf(currentKey) === 0} aria-label="Exercice précédent">
            <ArrowLeft size={16} />
          </button>
          <button onClick={handleSelectNext} className="btn btn-outline" disabled={exerciseKeys.indexOf(currentKey) === exerciseKeys.length - 1} aria-label="Exercice suivant">
            <ArrowRight size={16} />
          </button>
        </div>
      </div>

      {/* Statement Box */}
      <div className="exercise-sticky-context" style={{ background: '#0f172a', padding: '1rem', borderRadius: '8px', border: '1px solid #334155' }}>
        <h3 style={{ fontSize: '0.95rem', fontWeight: '600', marginBottom: '0.5rem', color: '#f8fafc' }}>{ex.title}</h3>
        <p style={{ fontSize: '0.9rem', color: '#cbd5e1', lineHeight: '1.5' }}>
          {renderKaTeX(ex.statement)}
        </p>
      </div>

      {/* Question Form */}
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        <label htmlFor="ex-answer-input" style={{ fontWeight: '600', fontSize: '0.9rem', color: '#60a5fa' }}>
          Question : {renderKaTeX(ex.question)}
        </label>

        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <input
            id="ex-answer-input"
            type="text"
            value={userAnswer}
            onChange={(e) => setUserAnswer(e.target.value)}
            placeholder="Saisis ta réponse numérique ou algébrique (ex: 64, -1, 5/3)..."
            style={{
              flex: 1,
              background: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '8px',
              padding: '0.6rem 0.85rem',
              color: '#f8fafc',
              fontSize: '0.9rem'
            }}
          />
          <button type="submit" className="btn btn-primary">Valider</button>
          <button
            type="button"
            onClick={() => setShowHint(!showHint)}
            className="btn btn-secondary"
            aria-label="Afficher l'indice"
          >
            <HelpCircle size={16} /> Indice
          </button>
        </div>
      </form>

      {/* Hint Box */}
      {showHint && (
        <div style={{ background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.3)', borderRadius: '8px', padding: '0.75rem', fontSize: '0.85rem', color: '#fbbf24' }}>
          <strong>Indice : </strong> {renderKaTeX(ex.hint)}
        </div>
      )}

      {/* Submission Feedback */}
      {submitted && (
        <div
          style={{
            background: isCorrect ? 'rgba(16, 185, 129, 0.15)' : 'rgba(244, 63, 94, 0.15)',
            border: `1px solid ${isCorrect ? '#10b981' : '#f43f5e'}`,
            borderRadius: '8px',
            padding: '1rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.5rem'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: '700', color: isCorrect ? '#34d399' : '#fda4af' }}>
            {isCorrect ? <CheckCircle size={20} /> : <AlertTriangle size={20} />}
            <span>{isCorrect ? 'Bravo ! Réponse exacte.' : 'Réponse incorrecte.'}</span>
          </div>

          <div style={{ fontSize: '0.875rem', color: '#cbd5e1' }}>
            <strong>Corrigé détaillé : </strong>
            <div>{renderKaTeX(ex.stepCorrection)}</div>
          </div>
        </div>
      )}
    </div>
  );
}
