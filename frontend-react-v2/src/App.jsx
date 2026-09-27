import React, { useState } from 'react';
import curriculumData from './data/mock_curriculum.json';
import { MIKAMIKE_MEDIA } from './data/mikamikeMedia';
import ResponsiveIllustration from './components/core/ResponsiveIllustration';

// Components
import LevelSelector from './components/LevelSelector';
import ConditionalSeriesSelector from './components/ConditionalSeriesSelector';
import SubjectSelector from './components/SubjectSelector';
import ProgramAdminBar from './components/ProgramAdminBar';
import ExamMode from './components/ExamMode';

// Sub-modules
import CanonicalGaussIntegration from './components/CanonicalGaussIntegration';
import AsmaPhotoModule from './components/AsmaPhotoModule';

// Core UI Tools
import ChatInterface from './components/core/ChatInterface';
import ExerciseViewer from './components/core/ExerciseViewer';
import MathKeyboard from './components/core/MathKeyboard';
import ArdoiseCanvas from './components/core/ArdoiseCanvas';
import MathTools from './components/core/MathTools';

// MikaMike Views with WP Media
import LoginScreen from './components/views/LoginScreen';
import StudentHomeView from './components/views/StudentHomeView';
import SubjectShowcaseView from './components/views/SubjectShowcaseView';
import CyclePathView from './components/views/CyclePathView';
import MikaInterfaceView from './components/views/MikaInterfaceView';
import ProgressView from './components/views/ProgressView';
import ParentSpaceView from './components/views/ParentSpaceView';
import EmptyStatesView from './components/views/EmptyStatesView';

import {
  Sparkles,
  Award,
  Edit2,
  Calculator,
  Grid,
  ChevronRight,
  Menu,
  X,
  Home,
  LogIn,
  BookOpen,
  Layers,
  Bot,
  TrendingUp,
  Heart,
  Coffee,
  CheckCircle2
} from 'lucide-react';

export default function App() {
  // Navigation & View state
  const [currentSection, setCurrentSection] = useState('accueil'); // 'accueil' | 'connexion' | 'matieres' | 'parcours' | 'mika' | 'progression' | 'parent' | 'exercices' | 'exam' | 'gauss_asma' | 'photo_asma' | 'attente'

  // Curriculum State
  const [selectedCycle, setSelectedCycle] = useState('lycee_general');
  const [selectedLevel, setSelectedLevel] = useState('1ere_g');
  const [selectedSeries, setSelectedSeries] = useState('');
  const [selectedSpecialty, setSelectedSpecialty] = useState('spe_maths');
  const [selectedOption, setSelectedOption] = useState('');
  const [selectedSubject, setSelectedSubject] = useState('maths');
  const [selectedExerciseId, setSelectedExerciseId] = useState('P1A1-006');

  // Floating & Drawer tool toggles
  const [showKeyboard, setShowKeyboard] = useState(false);
  const [showArdoise, setShowArdoise] = useState(false);
  const [showMathTools, setShowMathTools] = useState(false);
  const [keyboardInputBuffer, setKeyboardInputBuffer] = useState('');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const activeSubjectObj = curriculumData.subjects.find(s => s.id === selectedSubject) || curriculumData.subjects[0];
  const activeCycleObj = curriculumData.cycles.find(c => c.id === selectedCycle) || curriculumData.cycles[0];
  const activeLevelObj = activeCycleObj.levels.find(l => l.id === selectedLevel) || activeCycleObj.levels[0];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', width: '100vw', overflowX: 'hidden', backgroundColor: '#0f172a' }}>
      {/* 1. Top Local Program Admin Bar */}
      <ProgramAdminBar meta={curriculumData.meta} />

      {/* 2. Canonical MikaMike Application Header */}
      <header className="app-header">
        <div className="header-top">
          {/* Brand Logo with Official WP Mika Headshot */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer' }} onClick={() => setCurrentSection('accueil')}>
            <div style={{
              width: 42,
              height: 42,
              borderRadius: '12px',
              overflow: 'hidden',
              border: '2px solid #10b981',
              boxShadow: '0 4px 12px rgba(16, 185, 129, 0.4)'
            }}>
              <img
                src={MIKAMIKE_MEDIA.LOGO_PORTRAIT.remoteUrl}
                alt={MIKAMIKE_MEDIA.LOGO_PORTRAIT.alt}
                onError={(e) => { e.target.src = MIKAMIKE_MEDIA.LOGO_PORTRAIT.localUrl; }}
                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
              />
            </div>

            <div>
              <h1 style={{
                fontSize: '1.2rem',
                fontWeight: '900',
                letterSpacing: '-0.02em',
                background: 'linear-gradient(90deg, #34d399, #06b6d4, #3b82f6)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent'
              }}>
                MIKAMIKE <span style={{ fontSize: '0.75rem', fontWeight: '600', color: '#34d399', border: '1px solid rgba(52, 211, 153, 0.4)', padding: '1px 6px', borderRadius: '4px' }}>RC 2026</span>
              </h1>
              <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>
                Les sciences en confiance • {activeCycleObj.short_label} ({activeLevelObj.label})
              </div>
            </div>
          </div>

          {/* Level & Series Controls Cluster */}
          <div className="header-controls">
            <LevelSelector
              curriculum={curriculumData}
              selectedCycle={selectedCycle}
              selectedLevel={selectedLevel}
              onSelectCycle={(cycle) => {
                setSelectedCycle(cycle);
                setSelectedSeries('');
                setSelectedSpecialty('');
                setSelectedOption('');
              }}
              onSelectLevel={setSelectedLevel}
            />

            <ConditionalSeriesSelector
              curriculum={curriculumData}
              selectedCycle={selectedCycle}
              selectedLevel={selectedLevel}
              selectedSeries={selectedSeries}
              selectedSpecialty={selectedSpecialty}
              selectedOption={selectedOption}
              onSelectSeries={setSelectedSeries}
              onSelectSpecialty={setSelectedSpecialty}
              onSelectOption={setSelectedOption}
            />

            {/* Quick Login / Auth Status */}
            <button
              onClick={() => setCurrentSection('connexion')}
              className="btn btn-outline"
              style={{
                fontSize: '0.8rem',
                padding: '6px 12px',
                borderRadius: '8px',
                borderColor: 'rgba(16, 185, 129, 0.4)',
                color: '#34d399'
              }}
            >
              <LogIn size={14} /> Espace Client
            </button>

            {/* Mobile Menu Button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="mobile-toggle-btn btn btn-outline"
              aria-label="Ouvrir le menu mobile"
              style={{ display: 'none' }}
            >
              {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
          </div>
        </div>

        {/* Dynamic Section Navigation Bar */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0.5rem 1.25rem',
          background: 'rgba(15, 23, 42, 0.85)',
          borderTop: '1px solid var(--border-color)',
          flexWrap: 'wrap',
          gap: '0.75rem'
        }}>
          {/* Main Navigation Tabs */}
          <nav style={{ display: 'flex', gap: '0.35rem', overflowX: 'auto', paddingBottom: '2px', maxWidth: '100%' }}>
            <button
              onClick={() => setCurrentSection('accueil')}
              className={`btn ${currentSection === 'accueil' ? 'btn-primary' : 'btn-outline'}`}
              style={{ padding: '6px 12px', fontSize: '0.8rem', borderRadius: '8px', background: currentSection === 'accueil' ? '#10b981' : undefined }}
            >
              <Home size={14} /> Accueil Élève
            </button>

            <button
              onClick={() => setCurrentSection('matieres')}
              className={`btn ${currentSection === 'matieres' ? 'btn-primary' : 'btn-outline'}`}
              style={{ padding: '6px 12px', fontSize: '0.8rem', borderRadius: '8px', background: currentSection === 'matieres' ? '#0284c7' : undefined }}
            >
              <BookOpen size={14} /> Choix des Matières
            </button>

            <button
              onClick={() => setCurrentSection('parcours')}
              className={`btn ${currentSection === 'parcours' ? 'btn-primary' : 'btn-outline'}`}
              style={{ padding: '6px 12px', fontSize: '0.8rem', borderRadius: '8px', background: currentSection === 'parcours' ? '#f97316' : undefined }}
            >
              <Layers size={14} /> Parcours Scolaires
            </button>

            <button
              onClick={() => setCurrentSection('mika')}
              className={`btn ${currentSection === 'mika' ? 'btn-primary' : 'btn-outline'}`}
              style={{ padding: '6px 12px', fontSize: '0.8rem', borderRadius: '8px', background: currentSection === 'mika' ? '#0891b2' : undefined }}
            >
              <Bot size={14} /> Interface Mika IA
            </button>

            <button
              onClick={() => setCurrentSection('exercices')}
              className={`btn ${currentSection === 'exercices' ? 'btn-primary' : 'btn-outline'}`}
              style={{ padding: '6px 12px', fontSize: '0.8rem', borderRadius: '8px' }}
            >
              <Grid size={14} /> Exercices
            </button>

            <button
              onClick={() => setCurrentSection('progression')}
              className={`btn ${currentSection === 'progression' ? 'btn-primary' : 'btn-outline'}`}
              style={{ padding: '6px 12px', fontSize: '0.8rem', borderRadius: '8px', background: currentSection === 'progression' ? '#059669' : undefined }}
            >
              <TrendingUp size={14} /> Progression
            </button>

            <button
              onClick={() => setCurrentSection('parent')}
              className={`btn ${currentSection === 'parent' ? 'btn-primary' : 'btn-outline'}`}
              style={{ padding: '6px 12px', fontSize: '0.8rem', borderRadius: '8px', background: currentSection === 'parent' ? '#0284c7' : undefined }}
            >
              <Heart size={14} /> Espace Parent
            </button>

            <button
              onClick={() => setCurrentSection('exam')}
              className={`btn ${currentSection === 'exam' ? 'btn-primary' : 'btn-outline'}`}
              style={{ padding: '6px 12px', fontSize: '0.8rem', borderRadius: '8px' }}
            >
              <Award size={14} /> Annales Examen
            </button>

            <button
              onClick={() => setCurrentSection('gauss_asma')}
              className={`btn ${currentSection === 'gauss_asma' ? 'btn-primary' : 'btn-outline'}`}
              style={{ padding: '6px 12px', fontSize: '0.8rem', borderRadius: '8px', background: currentSection === 'gauss_asma' ? '#06b6d4' : undefined }}
            >
              <Sparkles size={14} /> Pivot Gauss
            </button>

            <button
              onClick={() => setCurrentSection('photo_asma')}
              className={`btn ${currentSection === 'photo_asma' ? 'btn-primary' : 'btn-outline'}`}
              style={{ padding: '6px 12px', fontSize: '0.8rem', borderRadius: '8px', background: currentSection === 'photo_asma' ? '#38bdf8' : undefined }}
            >
              📷 Photo Vision
            </button>

            <button
              onClick={() => setCurrentSection('attente')}
              className={`btn ${currentSection === 'attente' ? 'btn-primary' : 'btn-outline'}`}
              style={{ padding: '6px 12px', fontSize: '0.8rem', borderRadius: '8px' }}
            >
              <Coffee size={14} /> Pause
            </button>
          </nav>

          {/* Quick Tool Launchers */}
          <div style={{ display: 'flex', gap: '0.35rem' }}>
            <button
              onClick={() => setShowKeyboard(!showKeyboard)}
              className={`btn ${showKeyboard ? 'btn-primary' : 'btn-secondary'}`}
              style={{ padding: '4px 8px', fontSize: '0.75rem' }}
              aria-label="Basculer le clavier mathématique"
            >
              ⌨️ Clavier
            </button>
            <button
              onClick={() => setShowArdoise(!showArdoise)}
              className={`btn ${showArdoise ? 'btn-primary' : 'btn-secondary'}`}
              style={{ padding: '4px 8px', fontSize: '0.75rem' }}
              aria-label="Basculer l'ardoise graphique"
            >
              <Edit2 size={14} /> Ardoise
            </button>
            <button
              onClick={() => setShowMathTools(!showMathTools)}
              className={`btn ${showMathTools ? 'btn-primary' : 'btn-secondary'}`}
              style={{ padding: '4px 8px', fontSize: '0.75rem' }}
              aria-label="Basculer la calculatrice"
            >
              <Calculator size={14} /> Outils
            </button>
          </div>
        </div>
      </header>

      {/* 3. Main Multi-Level Stage Container */}
      <main className="main-layout" style={{ flex: 1, padding: '1rem', gap: '1rem' }}>
        {/* Left Sidebar: Subject & Curriculum Topics */}
        {currentSection !== 'connexion' && currentSection !== 'attente' && (
          <aside className="left-sidebar glass-card" style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.75rem', overflowY: 'auto' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <h3 style={{ fontSize: '0.8rem', fontWeight: '700', textTransform: 'uppercase', color: '#94a3b8', letterSpacing: '0.05em' }}>
                {activeSubjectObj.label} • {activeLevelObj.label}
              </h3>
              <span className="badge-disponible">RP-2026</span>
            </div>

            <SubjectSelector
              curriculum={curriculumData}
              selectedCycle={selectedCycle}
              selectedSubject={selectedSubject}
              onSelectSubject={setSelectedSubject}
            />

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.5rem' }}>
              {activeSubjectObj.chapters
                .filter(ch => ch.level === selectedLevel || ch.level === '1ere_g')
                .map(ch => (
                  <div
                    key={ch.id}
                    onClick={() => {
                      setSelectedExerciseId(ch.id);
                      if (currentSection !== 'exercices') setCurrentSection('exercices');
                    }}
                    style={{
                      background: '#0f172a',
                      border: selectedExerciseId === ch.id ? '1px solid #34d399' : '1px solid #334155',
                      borderRadius: '8px',
                      padding: '0.75rem',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '0.25rem',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '0.8rem', fontWeight: '600', color: '#f8fafc' }}>{ch.title}</span>
                      <span className={ch.coverage === 'Disponible' ? 'badge-disponible' : ch.coverage === 'Partiel' ? 'badge-partiel' : 'badge-preparation'}>
                        {ch.coverage}
                      </span>
                    </div>
                    <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>{ch.exercise_count} exercices interactifs</span>
                  </div>
                ))}
            </div>

            <div style={{ marginTop: 'auto', background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.3)', borderRadius: '8px', padding: '0.75rem', fontSize: '0.75rem', color: '#34d399' }}>
              💚 <strong>Doctrine MikaMike</strong> : Illustrations officielles WordPress validées. Zéro violet.
            </div>
          </aside>
        )}

        {/* Center Main Stage View Switcher */}
        <section style={{ display: 'flex', flexDirection: 'column', gap: '1rem', overflow: 'hidden', flex: 1 }}>
          <div style={{ flex: 1, overflowY: 'auto' }}>
            {currentSection === 'accueil' && (
              <StudentHomeView
                onNavigateSection={setCurrentSection}
                onSelectLevel={setSelectedLevel}
                onSelectSubject={setSelectedSubject}
              />
            )}

            {currentSection === 'connexion' && (
              <LoginScreen onLoginSuccess={() => setCurrentSection('accueil')} />
            )}

            {currentSection === 'matieres' && (
              <SubjectShowcaseView
                selectedSubject={selectedSubject}
                onSelectSubject={setSelectedSubject}
                onStartExercises={() => setCurrentSection('exercices')}
              />
            )}

            {currentSection === 'parcours' && (
              <CyclePathView
                selectedCycle={selectedCycle}
                selectedLevel={selectedLevel}
                onSelectCycle={setSelectedCycle}
                onSelectLevel={setSelectedLevel}
                onSelectSubject={setSelectedSubject}
                onStartExercises={() => setCurrentSection('exercices')}
              />
            )}

            {currentSection === 'mika' && (
              <MikaInterfaceView
                activeSubject={activeSubjectObj.label}
                activeLevel={activeLevelObj.label}
                activeExercise={selectedExerciseId}
                inputFormula={keyboardInputBuffer}
                onInputChange={setKeyboardInputBuffer}
              />
            )}

            {currentSection === 'exercices' && (
              <ExerciseViewer
                selectedExerciseId={selectedExerciseId}
                onExerciseChange={setSelectedExerciseId}
              />
            )}

            {currentSection === 'progression' && (
              <ProgressView
                selectedLevel={selectedLevel}
                selectedSubject={selectedSubject}
              />
            )}

            {currentSection === 'parent' && (
              <ParentSpaceView />
            )}

            {currentSection === 'exam' && (
              <ExamMode curriculum={curriculumData} />
            )}

            {currentSection === 'gauss_asma' && (
              <div style={{ height: '100%', overflowY: 'auto' }}>
                <CanonicalGaussIntegration />
              </div>
            )}

            {currentSection === 'photo_asma' && (
              <div style={{ height: '100%', overflowY: 'auto' }}>
                <AsmaPhotoModule />
              </div>
            )}

            {currentSection === 'attente' && (
              <EmptyStatesView type="pause" onRetry={() => setCurrentSection('exercices')} />
            )}
          </div>

          {/* Virtual Math Keyboard Drawer if toggled */}
          {showKeyboard && (
            <MathKeyboard
              onInsert={(latex) => setKeyboardInputBuffer(latex)}
              onClose={() => setShowKeyboard(false)}
            />
          )}
        </section>

        {/* Right Sidebar / Drawers */}
        {(showArdoise || showMathTools) && (
          <aside className="right-sidebar" style={{ display: 'flex', flexDirection: 'column', gap: '1rem', overflowY: 'auto' }}>
            {showArdoise && <ArdoiseCanvas />}
            {showMathTools && (
              <MathTools
                onClose={() => setShowMathTools(false)}
                onOpenGauss={() => setCurrentSection('gauss_asma')}
              />
            )}
          </aside>
        )}
      </main>
    </div>
  );
}
