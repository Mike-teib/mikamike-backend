import React from 'react';

/**
 * LevelSelector component:
 * Renders Cycle Selector and Sub-level Dropdown strictly driven by mock_curriculum.json.
 * Guarantees NO non-existent or invalid class is ever rendered.
 */
export default function LevelSelector({ curriculum, selectedCycle, selectedLevel, onSelectCycle, onSelectLevel }) {
  const activeCycle = curriculum.cycles.find(c => c.id === selectedCycle) || curriculum.cycles[0];

  const handleCycleChange = (e) => {
    const newCycleId = e.target.value;
    onSelectCycle(newCycleId);
    const newCycle = curriculum.cycles.find(c => c.id === newCycleId);
    if (newCycle && newCycle.levels.length > 0) {
      onSelectLevel(newCycle.levels[0].id);
    }
  };

  const handleLevelChange = (e) => {
    onSelectLevel(e.target.value);
  };

  return (
    <div className="selector-group" role="region" aria-label="Sélecteur de niveau scolaire">
      {/* Cycle Selector */}
      <label htmlFor="cycle-select" className="selector-label">Cycle / Voie</label>
      <select
        id="cycle-select"
        className="selector-select"
        value={selectedCycle}
        onChange={handleCycleChange}
        aria-label="Sélectionner le cycle ou la voie d'enseignement"
      >
        {curriculum.cycles.map(cycle => (
          <option key={cycle.id} value={cycle.id}>
            {cycle.short_label}
          </option>
        ))}
      </select>

      {/* Sub-level Selector */}
      <label htmlFor="level-select" className="selector-label" style={{ marginLeft: '0.5rem' }}>Classe</label>
      <select
        id="level-select"
        className="selector-select"
        value={selectedLevel}
        onChange={handleLevelChange}
        aria-label="Sélectionner la classe"
      >
        {activeCycle.levels.map(level => (
          <option key={level.id} value={level.id}>
            {level.label}
          </option>
        ))}
      </select>
    </div>
  );
}
