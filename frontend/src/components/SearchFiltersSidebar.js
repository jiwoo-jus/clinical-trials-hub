import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { Calendar } from 'lucide-react';

const SearchFilters = ({ onApplyFilters, isLoading, searchKey, filterStats }) => {
  console.log('[SearchFilters] Component rendered with filterStats:', !!filterStats);
  
  // Define filter options - simplified, removed complex phase
  const PHASE_OPTIONS = [
    { value: 'NA', label: 'N/A' },
    { value: 'EARLY_PHASE1', label: 'Early Phase 1' },
    { value: 'PHASE1', label: 'Phase 1' },
    { value: 'PHASE2', label: 'Phase 2' },
    { value: 'PHASE3', label: 'Phase 3' },
    { value: 'PHASE4', label: 'Phase 4' }
  ];
  
  const STUDY_TYPE_OPTIONS = [
    { value: 'INTERVENTIONAL', label: 'Interventional' },
    { value: 'OBSERVATIONAL', label: 'Observational' },
    { value: 'EXPANDED_ACCESS', label: 'Expanded Access' },
    { value: 'NA', label: 'N/A' }
  ];
  
  const DESIGN_ALLOCATION_OPTIONS = [
    { value: 'RANDOMIZED', label: 'Randomized' },
    { value: 'NON_RANDOMIZED', label: 'Non-randomized' },
    { value: 'NA', label: 'N/A' }
  ];
  
  const OBSERVATIONAL_MODEL_OPTIONS = [
    { value: 'COHORT', label: 'Cohort' },
    { value: 'CASE_CONTROL', label: 'Case-Control' },
    { value: 'CASE_ONLY', label: 'Case-Only' },
    { value: 'CASE_CROSSOVER', label: 'Case-Crossover' },
    { value: 'CROSS_SECTIONAL', label: 'Cross-Sectional' },
    { value: 'DEFINED_POPULATION', label: 'Defined Population'},
    { value: 'TIME_SERIES', label: 'Time-Series' },
    { value: 'ECOLOGIC_OR_COMMUNITY_STUDY', label: 'Ecologic/Community' },
    { value: 'FAMILY_BASED', label: 'Family-Based' },
    { value: 'OTHER', label: 'Other' },
    { value: 'NA', label: 'N/A' }
  ];

  // Initial state: all filters checked
  const getInitialFilters = () => ({
    study_type: STUDY_TYPE_OPTIONS.map(opt => opt.value),
    phase: PHASE_OPTIONS.map(opt => opt.value),
    design_allocation: DESIGN_ALLOCATION_OPTIONS.map(opt => opt.value),
    observational_model: OBSERVATIONAL_MODEL_OPTIONS.map(opt => opt.value),
    source_type: ['PM', 'CTG'],
    year_range: {
      from: null,
      to: null
    }
  });

  const [filters, setFilters] = useState(getInitialFilters());

  // Calculate dynamic counts - real-time calculation based on filterStats and current selection
  const getDynamicCount = (section, key, source = null) => {
    if (!filterStats) return 0;
    
    if (source) {
      return filterStats[source]?.[section]?.[key] || 0;
    } else {
      const pmCount = filterStats.pm?.[section]?.[key] || 0;
      const ctgCount = filterStats.ctg?.[section]?.[key] || 0;
      return pmCount + ctgCount;
    }
  };

  // Section clear handlers
  const handleClearPhase = () => {
    setFilters(prev => {
      const newFilters = { ...prev, phase: [] };
      // If both Phase and Design Allocation are empty, remove INTERVENTIONAL
      if (newFilters.design_allocation.length === 0) {
        newFilters.study_type = newFilters.study_type.filter(t => t !== 'INTERVENTIONAL');
      }
      return newFilters;
    });
  };

  const handleClearDesignAllocation = () => {
    setFilters(prev => {
      const newFilters = { ...prev, design_allocation: [] };
      // If both Design Allocation and Phase are empty, remove INTERVENTIONAL
      if (newFilters.phase.length === 0) {
        newFilters.study_type = newFilters.study_type.filter(t => t !== 'INTERVENTIONAL');
      }
      return newFilters;
    });
  };

  const handleClearObservationalModel = () => {
    setFilters(prev => {
      const newFilters = { ...prev, observational_model: [] };
      // If all Observational Models are cleared, remove OBSERVATIONAL
      newFilters.study_type = newFilters.study_type.filter(t => t !== 'OBSERVATIONAL');
      return newFilters;
    });
  };

  // Calculate 3-state for Study Type
  const getStudyTypeState = (studyType) => {
    const isSelected = filters.study_type.includes(studyType);
    
    if (studyType === 'INTERVENTIONAL') {
      const allPhases = PHASE_OPTIONS.map(opt => opt.value);
      const selectedPhases = filters.phase;
      const allAllocations = DESIGN_ALLOCATION_OPTIONS.map(opt => opt.value);
      const selectedAllocations = filters.design_allocation;
      
      if (isSelected && selectedPhases.length === allPhases.length && selectedAllocations.length === allAllocations.length) {
        return 'checked';
      } else if (isSelected && (selectedPhases.length < allPhases.length || selectedAllocations.length < allAllocations.length)) {
        return 'indeterminate';
      }
    }
    
    if (studyType === 'OBSERVATIONAL') {
      const allModels = OBSERVATIONAL_MODEL_OPTIONS.map(opt => opt.value);
      const selectedModels = filters.observational_model;
      
      if (isSelected && selectedModels.length === allModels.length) {
        return 'checked';
      } else if (isSelected && selectedModels.length < allModels.length) {
        return 'indeterminate';
      }
    }
    
    return isSelected ? 'checked' : 'unchecked';
  };

  // Parent-child filter relationship management
  const handleStudyTypeChange = (studyType) => {
    setFilters(prev => {
      const newFilters = { ...prev };
      
      if (prev.study_type.includes(studyType)) {
        // When unchecking parent, clear all children
        newFilters.study_type = prev.study_type.filter(t => t !== studyType);
        if (studyType === 'INTERVENTIONAL') {
          newFilters.phase = [];
          newFilters.design_allocation = [];
        } else if (studyType === 'OBSERVATIONAL') {
          newFilters.observational_model = [];
        }
      } else {
        // When checking parent, select all children
        newFilters.study_type = [...prev.study_type, studyType];
        if (studyType === 'INTERVENTIONAL') {
          newFilters.phase = PHASE_OPTIONS.map(opt => opt.value);
          newFilters.design_allocation = DESIGN_ALLOCATION_OPTIONS.map(opt => opt.value);
        } else if (studyType === 'OBSERVATIONAL') {
          newFilters.observational_model = OBSERVATIONAL_MODEL_OPTIONS.map(opt => opt.value);
        }
      }
      
      return newFilters;
    });
  };

  const handlePhaseChange = (phase) => {
    setFilters(prev => {
      const newPhases = prev.phase.includes(phase)
        ? prev.phase.filter(p => p !== phase)
        : [...prev.phase, phase];
      
      const newFilters = { ...prev, phase: newPhases };
      
      // If any phase is selected, automatically add INTERVENTIONAL
      if (newPhases.length > 0 && !prev.study_type.includes('INTERVENTIONAL')) {
        newFilters.study_type = [...prev.study_type, 'INTERVENTIONAL'];
      }
      // If both Phase and Design Allocation are empty, remove INTERVENTIONAL
      else if (newPhases.length === 0 && prev.design_allocation.length === 0) {
        newFilters.study_type = prev.study_type.filter(t => t !== 'INTERVENTIONAL');
      }
      
      return newFilters;
    });
  };

  const handleDesignAllocationChange = (allocation) => {
    setFilters(prev => {
      const newAllocations = prev.design_allocation.includes(allocation)
        ? prev.design_allocation.filter(a => a !== allocation)
        : [...prev.design_allocation, allocation];
      
      const newFilters = { ...prev, design_allocation: newAllocations };
      
      // If any allocation is selected, automatically add INTERVENTIONAL
      if (newAllocations.length > 0 && !prev.study_type.includes('INTERVENTIONAL')) {
        newFilters.study_type = [...prev.study_type, 'INTERVENTIONAL'];
      }
      // If both Design Allocation and Phase are empty, remove INTERVENTIONAL
      else if (newAllocations.length === 0 && prev.phase.length === 0) {
        newFilters.study_type = prev.study_type.filter(t => t !== 'INTERVENTIONAL');
      }
      
      return newFilters;
    });
  };

  const handleObservationalModelChange = (model) => {
    setFilters(prev => {
      const newModels = prev.observational_model.includes(model)
        ? prev.observational_model.filter(m => m !== model)
        : [...prev.observational_model, model];
      
      const newFilters = { ...prev, observational_model: newModels };
      
      // If any model is selected, automatically add OBSERVATIONAL
      if (newModels.length > 0 && !prev.study_type.includes('OBSERVATIONAL')) {
        newFilters.study_type = [...prev.study_type, 'OBSERVATIONAL'];
      }
      // If all models are cleared, remove OBSERVATIONAL
      else if (newModels.length === 0) {
        newFilters.study_type = prev.study_type.filter(t => t !== 'OBSERVATIONAL');
      }
      
      return newFilters;
    });
  };

  const handleSourceTypeChange = (source) => {
    setFilters(prev => ({
      ...prev,
      source_type: prev.source_type.includes(source)
        ? prev.source_type.filter(s => s !== source)
        : [...prev.source_type, source]
    }));
  };

  const handleYearRangeChange = (field, value) => {
    setFilters(prev => ({
      ...prev,
      year_range: {
        ...prev.year_range,
        [field]: value ? parseInt(value) : null
      }
    }));
  };

  const handleApply = () => {
    const filterData = {
      search_key: searchKey,
      phase: filters.phase.length > 0 ? filters.phase : null,
      study_type: filters.study_type.length > 0 ? filters.study_type : null,
      design_allocation: filters.design_allocation.length > 0 ? filters.design_allocation : null,
      observational_model: filters.observational_model.length > 0 ? filters.observational_model : null,
      source_type: filters.source_type.length > 0 ? filters.source_type : null,
      year_range: (filters.year_range.from || filters.year_range.to) ? filters.year_range : null
    };
    
    console.log('[SearchFilters] Sending filter data:', filterData);
    onApplyFilters(filterData);
  };

  const handleClear = () => {
    const initialFilters = getInitialFilters();
    setFilters(initialFilters);
  };

  // Get years from filter stats
  const getAvailableYears = () => {
    if (!filterStats) return [];
    
    const pmYears = Object.keys(filterStats.pm?.year || {});
    const ctgYears = Object.keys(filterStats.ctg?.year || {});
    const allYears = [...new Set([...pmYears, ...ctgYears])]
      .filter(year => year !== 'UNKNOWN')
      .map(year => parseInt(year))
      .filter(year => !isNaN(year))
      .sort((a, b) => b - a); // Descending order
    
    return allYears;
  };

  const availableYears = getAvailableYears();
  const minYear = availableYears.length > 0 ? Math.min(...availableYears) : new Date().getFullYear() - 10;
  const maxYear = availableYears.length > 0 ? Math.max(...availableYears) : new Date().getFullYear();

  return (
    <div className="w-full space-y-4">
      {/* Data Source */}
      <div className="bg-custom-bg-soft rounded-lg p-3 border border-custom-border">
        <h4 className="font-semibold mb-2 text-custom-text text-sm">Data Source</h4>
        <div className="space-y-2">
          {[
            { value: 'PM', label: 'PubMed', total: filterStats?.pm?.total || 0 },
            { value: 'CTG', label: 'ClinicalTrials.gov', total: filterStats?.ctg?.total || 0 }
          ].map(source => (
            <label key={source.value} className="flex items-center gap-2 cursor-pointer text-sm">
              <input
                type="checkbox"
                checked={filters.source_type.includes(source.value)}
                onChange={() => handleSourceTypeChange(source.value)}
                className="accent-custom-blue w-3 h-3 rounded border-gray-300"
              />
              <span className="text-custom-text font-medium flex-1">{source.label}</span>
              <span className="px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-600 text-xs font-semibold">
                {source.total}
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* Study Type Filter */}
      <div className="bg-custom-bg-soft rounded-lg p-3 border border-custom-border">
        <h4 className="font-semibold mb-2 text-custom-text text-sm">Study Type</h4>
        <div className="space-y-2">
          {STUDY_TYPE_OPTIONS.map(type => {
            const totalCount = getDynamicCount('study_type', type.value);
            const pmCount = getDynamicCount('study_type', type.value, 'pm');
            const ctgCount = getDynamicCount('study_type', type.value, 'ctg');
            const studyTypeState = getStudyTypeState(type.value);
            
            return (
              <div key={type.value} className="space-y-1">
                <label className={`flex items-center justify-between cursor-pointer text-sm ${totalCount === 0 ? 'opacity-50' : ''}`}>
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={studyTypeState === 'checked'}
                      ref={el => {
                        if (el) el.indeterminate = studyTypeState === 'indeterminate';
                      }}
                      onChange={() => handleStudyTypeChange(type.value)}
                      disabled={totalCount === 0}
                      className="accent-custom-blue w-3 h-3 rounded border-gray-300"
                    />
                    <span className="text-custom-text font-medium">{type.label}</span>
                    <span className="px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-600 text-xs font-semibold">
                      {totalCount}
                    </span>
                  </div>
                  <div className="flex gap-1">
                    {pmCount > 0 && (
                      <span className="bg-custom-blue-bg text-custom-blue text-xs px-1.5 py-0.5 rounded-full font-medium">{pmCount}</span>
                    )}
                    {ctgCount > 0 && (
                      <span className="bg-label-pubmed-bg text-label-pubmed-text text-xs px-1.5 py-0.5 rounded-full font-medium">{ctgCount}</span>
                    )}
                  </div>
                </label>
              </div>
            );
          })}
        </div>
      </div>

      {/* Phase */}
      <div className="bg-custom-bg-soft rounded-lg p-3 border border-custom-border">
        <div className="flex items-center justify-between mb-2">
          <h4 className="font-semibold text-custom-text text-sm">Study Phase</h4>
          <button 
            onClick={handleClearPhase}
            className="text-xs text-gray-600 hover:text-custom-blue"
          >
            Clear All
          </button>
        </div>
        <div className="space-y-1">
          {PHASE_OPTIONS.map(phaseObj => {
            const pmCount = getDynamicCount('phase', phaseObj.value, 'pm');
            const ctgCount = getDynamicCount('phase', phaseObj.value, 'ctg');
            const totalCount = pmCount + ctgCount;
            
            return (
              <label key={phaseObj.value} className={`flex items-center justify-between cursor-pointer text-sm ${totalCount === 0 ? 'opacity-50' : ''}`}>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={filters.phase.includes(phaseObj.value)}
                    onChange={() => handlePhaseChange(phaseObj.value)}
                    disabled={totalCount === 0}
                    className="accent-custom-blue w-3 h-3 rounded border-gray-300"
                  />
                  <span className="text-custom-text font-medium">{phaseObj.label}</span>
                  <span className="px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-600 text-xs font-semibold">
                    {totalCount}
                  </span>
                </div>
                <div className="flex gap-1">
                  {pmCount > 0 && (
                    <span className="bg-custom-blue-bg text-custom-blue text-xs px-1.5 py-0.5 rounded-full font-medium">{pmCount}</span>
                  )}
                  {ctgCount > 0 && (
                    <span className="bg-label-pubmed-bg text-label-pubmed-text text-xs px-1.5 py-0.5 rounded-full font-medium">{ctgCount}</span>
                  )}
                </div>
              </label>
            );
          })}
        </div>
      </div>

      {/* Design Allocation */}
      <div className="bg-custom-bg-soft rounded-lg p-3 border border-custom-border">
        <div className="flex items-center justify-between mb-2">
          <h4 className="font-semibold text-custom-text text-sm">Design Allocation</h4>
          <button 
            onClick={handleClearDesignAllocation}
            className="text-xs text-gray-600 hover:text-custom-blue"
          >
            Clear All
          </button>
        </div>
        <div className="space-y-1">
          {DESIGN_ALLOCATION_OPTIONS.map(allocation => {
            const pmCount = getDynamicCount('design_allocation', allocation.value, 'pm');
            const ctgCount = getDynamicCount('design_allocation', allocation.value, 'ctg');
            const totalCount = pmCount + ctgCount;
            
            return (
              <label key={allocation.value} className={`flex items-center justify-between cursor-pointer text-sm ${totalCount === 0 ? 'opacity-50' : ''}`}>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={filters.design_allocation.includes(allocation.value)}
                    onChange={() => handleDesignAllocationChange(allocation.value)}
                    disabled={totalCount === 0}
                    className="accent-custom-blue w-3 h-3 rounded border-gray-300"
                  />
                  <span className="text-custom-text font-medium">{allocation.label}</span>
                  <span className="px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-600 text-xs font-semibold">
                    {totalCount}
                  </span>
                </div>
                <div className="flex gap-1">
                  {pmCount > 0 && (
                    <span className="bg-custom-blue-bg text-custom-blue text-xs px-1.5 py-0.5 rounded-full font-medium">{pmCount}</span>
                  )}
                  {ctgCount > 0 && (
                    <span className="bg-label-pubmed-bg text-label-pubmed-text text-xs px-1.5 py-0.5 rounded-full font-medium">{ctgCount}</span>
                  )}
                </div>
              </label>
            );
          })}
        </div>
      </div>

      {/* Observational Model */}
      <div className="bg-custom-bg-soft rounded-lg p-3 border border-custom-border">
        <div className="flex items-center justify-between mb-2">
          <h4 className="font-semibold text-custom-text text-sm">Study Model</h4>
          <button 
            onClick={handleClearObservationalModel}
            className="text-xs text-gray-600 hover:text-custom-blue"
          >
            Clear All
          </button>
        </div>
        <div className="space-y-1">
          {OBSERVATIONAL_MODEL_OPTIONS.map(model => {
            const pmCount = getDynamicCount('observational_model', model.value, 'pm');
            const ctgCount = getDynamicCount('observational_model', model.value, 'ctg');
            const totalCount = pmCount + ctgCount;
            
            return (
              <label key={model.value} className={`flex items-center justify-between cursor-pointer text-sm ${totalCount === 0 ? 'opacity-50' : ''}`}>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={filters.observational_model.includes(model.value)}
                    onChange={() => handleObservationalModelChange(model.value)}
                    disabled={totalCount === 0}
                    className="accent-custom-blue w-3 h-3 rounded border-gray-300"
                  />
                  <span className="text-custom-text font-medium">{model.label}</span>
                  <span className="px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-600 text-xs font-semibold">
                    {totalCount}
                  </span>
                </div>
                <div className="flex gap-1">
                  {pmCount > 0 && (
                    <span className="bg-custom-blue-bg text-custom-blue text-xs px-1.5 py-0.5 rounded-full font-medium">{pmCount}</span>
                  )}
                  {ctgCount > 0 && (
                    <span className="bg-label-pubmed-bg text-label-pubmed-text text-xs px-1.5 py-0.5 rounded-full font-medium">{ctgCount}</span>
                  )}
                </div>
              </label>
            );
          })}
        </div>
      </div>

      {/* Year Range */}
      <div className="bg-custom-bg-soft rounded-lg p-3 border border-custom-border">
        <h4 className="font-semibold mb-2 flex items-center gap-1 text-custom-text text-sm">
          <Calendar size={14} />
          Year Range
        </h4>
        <div className="space-y-2">
          <div className="flex gap-1 items-center">
            <select
              value={filters.year_range.from || ''}
              onChange={(e) => handleYearRangeChange('from', e.target.value)}
              className="border border-custom-border rounded px-1 py-1 text-xs bg-white flex-1"
            >
              <option value="">From</option>
              {Array.from({length: maxYear - minYear + 1}, (_, i) => maxYear - i).map(year => (
                <option key={year} value={year}>{year}</option>
              ))}
            </select>
            <span className="text-xs text-custom-text">to</span>
            <select
              value={filters.year_range.to || ''}
              onChange={(e) => handleYearRangeChange('to', e.target.value)}
              className="border border-custom-border rounded px-1 py-1 text-xs bg-white flex-1"
            >
              <option value="">To</option>
              {Array.from({length: maxYear - minYear + 1}, (_, i) => maxYear - i).map(year => (
                <option key={year} value={year}>{year}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex gap-2 pt-2 border-t border-gray-200">
        <button
          onClick={handleApply}
          disabled={isLoading}
          className="flex-1 px-3 py-2 bg-custom-blue text-white rounded-lg font-semibold text-sm shadow-sm hover:bg-custom-blue-hover disabled:opacity-50 transition"
        >
          {isLoading ? 'Applying...' : 'Apply'}
        </button>
        <button
          onClick={handleClear}
          disabled={isLoading}
          className="px-3 py-2 border border-custom-border rounded-lg font-semibold text-custom-text bg-white hover:bg-gray-50 disabled:opacity-50 transition text-sm"
        >
          Reset
        </button>
      </div>
    </div>
  );
};

SearchFilters.propTypes = {
  onApplyFilters: PropTypes.func.isRequired,
  isLoading: PropTypes.bool,
  searchKey: PropTypes.string,
  filterStats: PropTypes.shape({
    pm: PropTypes.shape({
      total: PropTypes.number,
      phase: PropTypes.object,
      study_type: PropTypes.object,
      year: PropTypes.object,
      design_allocation: PropTypes.object,
      observational_model: PropTypes.object
    }),
    ctg: PropTypes.shape({
      total: PropTypes.number,
      phase: PropTypes.object,
      study_type: PropTypes.object,
      year: PropTypes.object,
      design_allocation: PropTypes.object,
      observational_model: PropTypes.object
    })
  })
};

export default SearchFilters;
