import React, { useState } from 'react';
import { MIKAMIKE_MEDIA } from '../../data/mikamikeMedia';
import ResponsiveIllustration from '../core/ResponsiveIllustration';
import { Award, Sparkles, BookOpen, CheckCircle, ArrowRight } from 'lucide-react';

export default function CyclePathView({
  selectedCycle,
  selectedLevel,
  onSelectCycle,
  onSelectLevel,
  onSelectSubject,
  onStartExercises
}) {
  const [activeCycleTab, setActiveCycleTab] = useState(selectedCycle || 'lycee_general');

  const cyclesConfig = {
    primaire: {
      title: 'Parcours Primaire (CP, CE1, CE2, CM1, CM2)',
      badge: 'CP à CM2',
      badgeColor: '#10b981',
      tagline: 'Poser de solides bases en calcul, géométrie et initiation aux sciences',
      illustration: MIKAMIKE_MEDIA.CYCLE_SELECTOR_3D,
      levels: [
        { id: 'cp', label: 'CP', desc: 'Découverte des nombres et formes' },
        { id: 'ce1', label: 'CE1', desc: 'Calcul mental et repérage spatial' },
        { id: 'ce2', label: 'CE2', desc: 'Opérations et premières mesures' },
        { id: 'cm1', label: 'CM1', desc: 'Fractions et démarche scientifique' },
        { id: 'cm2', label: 'CM2', desc: 'Consolidation et préparation collège' }
      ],
      recommendedTeacher: MIKAMIKE_MEDIA.SVT_PROF,
      teacherTitle: 'Mika Découverte des Sciences'
    },
    college: {
      title: 'Parcours Collège (6ème, 5ème, 4ème, 3ème)',
      badge: '6ème à 3ème',
      badgeColor: '#0284c7',
      tagline: 'Renforcer l\'autonomie, comprendre les formules et préparer le Brevet',
      illustration: MIKAMIKE_MEDIA.CYCLE_SELECTOR_3D,
      levels: [
        { id: '6eme', label: '6ème', desc: 'Cycle de consolidation mathématique' },
        { id: '5eme', label: '5ème', desc: 'Physique-Chimie & SVT intégrées' },
        { id: '4eme', label: '4ème', desc: 'Équations, théorème de Pythagore' },
        { id: '3eme', label: '3ème', desc: 'Préparation au DNB et théorème de Thalès' }
      ],
      recommendedTeacher: MIKAMIKE_MEDIA.PHYSICS_PROF,
      teacherTitle: 'Mika Professeur du Collège'
    },
    lycee_general: {
      title: 'Parcours Lycée Général (2nde, 1ère G, Terminale G)',
      badge: '2nde, 1ère, Tle Générale',
      badgeColor: '#f97316',
      tagline: 'Spécialités Maths, Physique-Chimie, SVT & Épreuves du Bac',
      illustration: MIKAMIKE_MEDIA.CYCLE_SELECTOR_3D,
      levels: [
        { id: '2nde', label: '2nde Générale', desc: 'Fonctions, vecteurs, physique & chimie' },
        { id: '1ere_g', label: '1ère Générale', desc: 'Spécialités Maths / PC / SVT' },
        { id: 'terminale_g', label: 'Terminale Générale', desc: 'Préparation intensive au Baccalauréat' }
      ],
      recommendedTeacher: MIKAMIKE_MEDIA.MATHS_PROF,
      teacherTitle: 'Mika Professeur Lycée Général'
    },
    lycee_techno: {
      title: 'Parcours Lycée Technologique (STI2D, STMG, STL, ST2S)',
      badge: '1ère & Tle Technologique',
      badgeColor: '#0891b2',
      tagline: 'Mathématiques appliquées, Physique-Chimie industrielle et laboratoire',
      illustration: MIKAMIKE_MEDIA.CYCLE_SELECTOR_3D,
      levels: [
        { id: '1ere_sti2d', label: '1ère STI2D', desc: 'Maths appliquées & ingénierie' },
        { id: 'term_sti2d', label: 'Terminale STI2D', desc: 'Physique, énergie & systèmes' },
        { id: '1ere_stmg', label: '1ère STMG', desc: 'Mathématiques de gestion' },
        { id: 'term_stmg', label: 'Terminale STMG', desc: 'Statistiques & optimisation' },
        { id: '1ere_stl', label: '1ère / Tle STL', desc: 'Biotechnologies & chimie physique' }
      ],
      recommendedTeacher: MIKAMIKE_MEDIA.CHEMISTRY_PROF,
      teacherTitle: 'Mika Professeur Lycée Techno'
    }
  };

  const activeObj = cyclesConfig[activeCycleTab] || cyclesConfig['lycee_general'];

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      
      {/* Top Cycle Switcher Tabs */}
      <div className="glass-card" style={{ padding: '0.75rem', borderRadius: '16px', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
        <button
          type="button"
          onClick={() => { setActiveCycleTab('primaire'); onSelectCycle && onSelectCycle('primaire'); }}
          style={{
            flex: 1,
            minWidth: '160px',
            padding: '0.75rem 1rem',
            borderRadius: '10px',
            border: 'none',
            background: activeCycleTab === 'primaire' ? 'linear-gradient(135deg, #10b981, #059669)' : '#0f172a',
            color: activeCycleTab === 'primaire' ? '#fff' : '#94a3b8',
            fontWeight: '700',
            fontSize: '0.85rem',
            cursor: 'pointer',
            transition: 'all 0.2s ease'
          }}
        >
          🌱 Primaire (CP-CM2)
        </button>

        <button
          type="button"
          onClick={() => { setActiveCycleTab('college'); onSelectCycle && onSelectCycle('college'); }}
          style={{
            flex: 1,
            minWidth: '160px',
            padding: '0.75rem 1rem',
            borderRadius: '10px',
            border: 'none',
            background: activeCycleTab === 'college' ? 'linear-gradient(135deg, #0284c7, #0369a1)' : '#0f172a',
            color: activeCycleTab === 'college' ? '#fff' : '#94a3b8',
            fontWeight: '700',
            fontSize: '0.85rem',
            cursor: 'pointer',
            transition: 'all 0.2s ease'
          }}
        >
          🚀 Collège (6e-3e)
        </button>

        <button
          type="button"
          onClick={() => { setActiveCycleTab('lycee_general'); onSelectCycle && onSelectCycle('lycee_general'); }}
          style={{
            flex: 1,
            minWidth: '160px',
            padding: '0.75rem 1rem',
            borderRadius: '10px',
            border: 'none',
            background: activeCycleTab === 'lycee_general' ? 'linear-gradient(135deg, #f97316, #ea580c)' : '#0f172a',
            color: activeCycleTab === 'lycee_general' ? '#fff' : '#94a3b8',
            fontWeight: '700',
            fontSize: '0.85rem',
            cursor: 'pointer',
            transition: 'all 0.2s ease'
          }}
        >
          🎓 Lycée Général
        </button>

        <button
          type="button"
          onClick={() => { setActiveCycleTab('lycee_techno'); onSelectCycle && onSelectCycle('lycee_techno'); }}
          style={{
            flex: 1,
            minWidth: '160px',
            padding: '0.75rem 1rem',
            borderRadius: '10px',
            border: 'none',
            background: activeCycleTab === 'lycee_techno' ? 'linear-gradient(135deg, #0891b2, #0e7490)' : '#0f172a',
            color: activeCycleTab === 'lycee_techno' ? '#fff' : '#94a3b8',
            fontWeight: '700',
            fontSize: '0.85rem',
            cursor: 'pointer',
            transition: 'all 0.2s ease'
          }}
        >
          🔬 Lycée Technologique
        </button>
      </div>

      {/* Cycle Banner Details */}
      <div className="glass-card" style={{
        padding: '1.75rem',
        borderRadius: '20px',
        background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.9), rgba(6, 182, 212, 0.15))',
        border: `1px solid ${activeObj.badgeColor}`,
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
        gap: '2rem',
        alignItems: 'center'
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.5rem',
            background: activeObj.badgeColor,
            color: '#fff',
            padding: '4px 12px',
            borderRadius: '9999px',
            fontSize: '0.8rem',
            fontWeight: '700',
            width: 'fit-content'
          }}>
            <Award size={14} /> {activeObj.badge}
          </div>

          <h2 style={{ fontSize: '1.8rem', fontWeight: '800', color: '#f8fafc' }}>
            {activeObj.title}
          </h2>

          <p style={{ color: '#94a3b8', fontSize: '0.95rem', lineHeight: 1.6 }}>
            {activeObj.tagline}
          </p>
        </div>

        <div>
          <ResponsiveIllustration
            media={activeObj.recommendedTeacher}
            aspectRatio="4/3"
            altOverride={activeObj.teacherTitle}
          />
        </div>
      </div>

      {/* Levels Breakdown Cards */}
      <div>
        <h3 style={{ fontSize: '1.2rem', fontWeight: '700', color: '#f8fafc', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <BookOpen size={18} color={activeObj.badgeColor} /> Niveaux disponibles dans ce parcours
        </h3>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
          {activeObj.levels.map((lvl) => {
            const isSelectedLvl = selectedLevel === lvl.id;
            return (
              <div
                key={lvl.id}
                className="glass-card"
                onClick={() => {
                  onSelectLevel && onSelectLevel(lvl.id);
                  onStartExercises && onStartExercises();
                }}
                style={{
                  padding: '1.25rem',
                  borderRadius: '14px',
                  background: isSelectedLvl ? 'rgba(16, 185, 129, 0.2)' : '#0f172a',
                  border: isSelectedLvl ? '2px solid #34d399' : '1px solid #334155',
                  cursor: 'pointer',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.5rem',
                  transition: 'all 0.2s ease'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '1.1rem', fontWeight: '800', color: '#f8fafc' }}>{lvl.label}</span>
                  {isSelectedLvl && <CheckCircle size={18} color="#34d399" />}
                </div>
                <p style={{ fontSize: '0.8rem', color: '#94a3b8' }}>{lvl.desc}</p>

                <div style={{ marginTop: 'auto', paddingTop: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.25rem', color: '#38bdf8', fontSize: '0.75rem', fontWeight: '600' }}>
                  Voir les cours & exercices <ArrowRight size={14} />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
