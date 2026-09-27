import React from 'react';
import { Calculator, Zap, Leaf } from 'lucide-react';

const ICON_MAP = {
  Calculator: Calculator,
  Zap: Zap,
  Leaf: Leaf
};

/**
 * SubjectSelector Component:
 * Dynamically filters applicable subjects (Maths, Physique-Chimie, SVT) for the active cycle/level.
 * Renders subject tabs with coverage state indicators.
 */
export default function SubjectSelector({ curriculum, selectedCycle, selectedSubject, onSelectSubject }) {
  // Filter subjects applicable to the selected cycle
  const validSubjects = curriculum.subjects.filter(subj =>
    subj.applicable_cycles.includes(selectedCycle)
  );

  return (
    <div className="subject-selector" role="region" aria-label="Sélecteur de matière">
      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
        {validSubjects.map(subject => {
          const IconComponent = ICON_MAP[subject.icon] || Calculator;
          const isSelected = selectedSubject === subject.id;

          let badgeClass = 'badge-disponible';
          if (subject.coverage === 'Partiel') badgeClass = 'badge-partiel';
          if (subject.coverage === 'En préparation') badgeClass = 'badge-preparation';

          return (
            <button
              key={subject.id}
              onClick={() => onSelectSubject(subject.id)}
              className={`btn ${isSelected ? 'btn-primary' : 'btn-outline'}`}
              style={{
                borderColor: isSelected ? subject.color : undefined,
                backgroundColor: isSelected ? subject.color : undefined
              }}
              aria-pressed={isSelected}
              aria-label={`Matière ${subject.label}, statut ${subject.coverage}`}
            >
              <IconComponent size={16} />
              <span>{subject.label}</span>
              <span className={badgeClass} style={{ marginLeft: '4px' }}>
                {subject.coverage}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
