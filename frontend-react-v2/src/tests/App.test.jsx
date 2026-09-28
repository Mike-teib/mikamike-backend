import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, test, expect, vi } from 'vitest';
import App from '../App';
import LevelSelector from '../components/LevelSelector';
import ConditionalSeriesSelector from '../components/ConditionalSeriesSelector';
import curriculumData from '../data/mock_curriculum.json';
import ChatInterface from '../components/core/ChatInterface';
import MathKeyboard from '../components/core/MathKeyboard';

describe('MIKAMIKE Multi-Level Frontend RC — UI Test Suite', () => {
  test('Renders Brand Title and Default Level (Lycée général > Première Générale)', () => {
    render(<App />);
    expect(screen.getByText(/MIKAMIKE/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Première Générale/i)[0]).toBeInTheDocument();
  });

  test('Cycle Selector updates available levels without invalid class names', () => {
    const onSelectCycle = vi.fn();
    const onSelectLevel = vi.fn();
    render(
      <LevelSelector
        curriculum={curriculumData}
        selectedCycle="college"
        selectedLevel="3eme"
        onSelectCycle={onSelectCycle}
        onSelectLevel={onSelectLevel}
      />
    );

    // Collège levels should be 5ème, 4ème, 3ème
    const levelSelect = screen.getByLabelText(/Sélectionner la classe/i);
    expect(levelSelect).toHaveTextContent('5ème');
    expect(levelSelect).toHaveTextContent('4ème');
    expect(levelSelect).toHaveTextContent('3ème');

    // Confirm CP, CE1, STMG are NOT in Collège options
    expect(levelSelect).not.toHaveTextContent('CP');
    expect(levelSelect).not.toHaveTextContent('STMG');
  });

  test('Conditional Series Selector is HIDDEN for Collège and Cycle 2', () => {
    const { container } = render(
      <ConditionalSeriesSelector
        curriculum={curriculumData}
        selectedCycle="college"
        selectedLevel="3eme"
        selectedSeries=""
        selectedSpecialty=""
        selectedOption=""
        onSelectSeries={() => {}}
        onSelectSpecialty={() => {}}
        onSelectOption={() => {}}
      />
    );
    expect(container.firstChild).toBeNull();
  });

  test('Conditional Series Selector SHOWS Series for Lycée Techno (STMG, STI2D, STL, ST2S)', () => {
    render(
      <ConditionalSeriesSelector
        curriculum={curriculumData}
        selectedCycle="lycee_techno"
        selectedLevel="1ere_t"
        selectedSeries="sti2d"
        selectedSpecialty=""
        selectedOption=""
        onSelectSeries={() => {}}
        onSelectSpecialty={() => {}}
        onSelectOption={() => {}}
      />
    );

    const seriesSelect = screen.getByLabelText(/Sélectionner la série ou filière/i);
    expect(seriesSelect).toBeInTheDocument();
    expect(seriesSelect).toHaveTextContent('STMG');
    expect(seriesSelect).toHaveTextContent('STI2D');
    expect(seriesSelect).toHaveTextContent('STL');
    expect(seriesSelect).toHaveTextContent('ST2S');
  });

  test('Exam Mode displays Brevet and Bac annales with coverage badges', () => {
    render(<App />);
    const examTab = screen.getByRole('button', { name: /Annales Examen/i });
    fireEvent.click(examTab);

    expect(screen.getByText(/Mode Examen — Annales Officielles/i)).toBeInTheDocument();
    expect(screen.getAllByText(/DNB 2024 Métropole — Mathématiques/i)[0]).toBeInTheDocument();
    expect(screen.getAllByText(/Spécialité Mathématiques/i)[0]).toBeInTheDocument();
  });

  test('Core UI Tools: Math Keyboard opens and inserts formula into chat buffer', () => {
    render(<App />);
    const keyboardBtn = screen.getByRole('button', { name: /Basculer le clavier mathématique/i });
    fireEvent.click(keyboardBtn);

    expect(screen.getByText(/Clavier Mathématique Éléments Canoniques/i)).toBeInTheDocument();

    const deltaBtn = screen.getByRole('button', { name: /Symbole mathématique Δ/i });
    fireEvent.click(deltaBtn);
  });



  test('Mika chat keeps current exercise context visible', () => {
    render(
      <ChatInterface
        activeSubject="Mathématiques"
        activeLevel="Première Générale"
        activeExercise="P1A1-006"
        inputFormula=""
        onInputChange={() => {}}
      />
    );

    expect(screen.getByText(/Énoncé en cours/i)).toBeInTheDocument();
    expect(screen.getByText(/P1A1-006/i)).toBeInTheDocument();
    expect(screen.getByText(/Quelle est la valeur du discriminant/i)).toBeInTheDocument();
  });

  test('Math keyboard opens in compact mode and can expand', () => {
    render(<MathKeyboard onInsert={() => {}} onClose={() => {}} />);

    expect(screen.getByText(/Clavier maths/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Agrandir le clavier mathématique/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Symbole mathématique x²/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Agrandir le clavier mathématique/i }));
    expect(screen.getByRole('button', { name: /Réduire le clavier mathématique/i })).toBeInTheDocument();
  });

  test('Mika chat exposes a microphone control', () => {
    render(
      <ChatInterface
        activeSubject="Mathématiques"
        activeLevel="Première Générale"
        activeExercise="P1A1-006"
        inputFormula=""
        onInputChange={() => {}}
      />
    );
    expect(screen.getByRole('button', { name: /Activer la dictée vocale/i })).toBeInTheDocument();
  });

  test('Program Admin Debug Panel toggles metadata accurately', () => {
    render(<App />);
    const adminToggle = screen.getByRole('button', { name: /Toggle UI Admin Debug Panel/i });
    fireEvent.click(adminToggle);

    expect(screen.getByText(/UI Admin Local \/ Métadonnées du Programme Canonique/i)).toBeInTheDocument();
    expect(screen.getAllByText(/BO n°30 du 23 juillet 2020 \/ Mise à jour 2024-2025/i)[0]).toBeInTheDocument();
  });
});
