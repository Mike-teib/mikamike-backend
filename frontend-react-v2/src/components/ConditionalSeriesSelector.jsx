import React from 'react';

/**
 * ConditionalSeriesSelector Component:
 * Conditionally renders Series, Specialties, and Options depending on selected cycle & level.
 * Completely hidden for Collège, Cycle 2, Cycle 3 when series/specialties do not apply.
 */
export default function ConditionalSeriesSelector({
  curriculum,
  selectedCycle,
  selectedLevel,
  selectedSeries,
  selectedSpecialty,
  selectedOption,
  onSelectSeries,
  onSelectSpecialty,
  onSelectOption
}) {
  const activeCycle = curriculum.cycles.find(c => c.id === selectedCycle);
  const activeLevelObj = activeCycle?.levels.find(l => l.id === selectedLevel);

  const hasSeries = activeCycle?.has_series || activeLevelObj?.has_series;
  const hasSpecialties = activeCycle?.has_specialties || activeLevelObj?.has_specialties;
  const hasOptions = activeCycle?.has_options || activeLevelObj?.has_options;

  // Determine available series
  const seriesList = curriculum.series[selectedCycle] || [];

  // Determine available specialties
  let specialtyList = [];
  if (selectedCycle === 'lycee_general') {
    specialtyList = curriculum.specialties.lycee_general || [];
  } else if (selectedSeries && curriculum.specialties[selectedSeries]) {
    specialtyList = curriculum.specialties[selectedSeries] || [];
  }

  // Determine available options
  const optionsList = curriculum.options[selectedLevel] || [];

  // If no series, specialties, or options apply, render nothing
  if (!hasSeries && !hasSpecialties && !hasOptions && seriesList.length === 0 && specialtyList.length === 0 && optionsList.length === 0) {
    return null;
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
      {/* Series Selector (Techno & Voie Pro) */}
      {seriesList.length > 0 && (
        <div className="selector-group">
          <label htmlFor="series-select" className="selector-label">Série / Filière</label>
          <select
            id="series-select"
            className="selector-select"
            value={selectedSeries || ''}
            onChange={(e) => onSelectSeries(e.target.value)}
            aria-label="Sélectionner la série ou filière"
          >
            <option value="">-- Sélectionner une série --</option>
            {seriesList.map(item => (
              <option key={item.id} value={item.id} title={item.name}>
                {item.label}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Specialty Selector (Lycée Général or Techno) */}
      {hasSpecialties && specialtyList.length > 0 && (
        <div className="selector-group">
          <label htmlFor="specialty-select" className="selector-label">Spécialité</label>
          <select
            id="specialty-select"
            className="selector-select"
            value={selectedSpecialty || ''}
            onChange={(e) => onSelectSpecialty(e.target.value)}
            aria-label="Sélectionner la spécialité"
          >
            <option value="">-- Sélectionner une spécialité --</option>
            {specialtyList.map(spe => (
              <option key={spe.id} value={spe.id}>
                {spe.label}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Option Selector (e.g. Maths Expertes/Complémentaires in Tle) */}
      {hasOptions && optionsList.length > 0 && (
        <div className="selector-group">
          <label htmlFor="option-select" className="selector-label">Option</label>
          <select
            id="option-select"
            className="selector-select"
            value={selectedOption || ''}
            onChange={(e) => onSelectOption(e.target.value)}
            aria-label="Sélectionner l'option"
          >
            <option value="">-- Sans option --</option>
            {optionsList.map(opt => (
              <option key={opt.id} value={opt.id}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      )}
    </div>
  );
}
