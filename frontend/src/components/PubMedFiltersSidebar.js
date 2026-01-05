import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { filterLogger } from '../utils/logger';

const PubMedFiltersSidebar = ({ onApplyFilters, isLoading, searchKey, filterStats, filters: externalFilters, setFilters: setExternalFilters }) => {
  filterLogger.debug('Component rendered with filterStats:', filterStats);
  filterLogger.debug('CTG filters from filterStats:', filterStats?.ctg_filters);

  // Phase filters - applicable to both PM and CTG
  const PHASE_OPTIONS = [
    { value: 'phase_i', label: 'Phase I', backendKey: 'phase_i' },
    { value: 'phase_ii', label: 'Phase II', backendKey: 'phase_ii' },
    { value: 'phase_iii', label: 'Phase III', backendKey: 'phase_iii' },
    { value: 'phase_iv', label: 'Phase IV', backendKey: 'phase_iv' }
  ];

  // Study type filters - applicable to both PM and CTG
  const STUDY_TYPE_OPTIONS = [
    { value: 'clinical_trial', label: 'Clinical Trial', backendKey: 'clinical_trial' },
    { value: 'randomized_controlled_trial', label: 'Randomized Controlled Trial', backendKey: 'randomized_controlled_trial' },
    { value: 'observational', label: 'Observational Study', backendKey: 'observational' }
  ];

  // PubMed-only filters - these only apply to PubMed search
  const PUBMED_ONLY_ARTICLE_TYPES = [
    { value: 'meta_analysis', label: 'Meta-Analysis', backendKey: 'meta_analysis' },
    { value: 'review', label: 'Review', backendKey: 'review' },
    { value: 'systematic_review', label: 'Systematic Review', backendKey: 'systematic_review' }
  ];

  const PUBMED_ONLY_SPECIES = [
    { value: 'humans', label: 'Humans', backendKey: 'humans' },
    { value: 'other_animals', label: 'Other Animals', backendKey: 'other_animals' }
  ];

  // CTG-only filters - placeholder for future CTG-specific filters
  const CTG_ONLY_OPTIONS = [
    // Future: Add CTG-specific filters here
    // Example: { value: 'expanded_access', label: 'Expanded Access', backendKey: 'expanded_access' }
  ];

  const AGE_OPTIONS = [
    { value: 'child_0_18', label: 'Child: 0-18 years', backendKey: 'child_0_18' },
    { value: 'adult_19_plus', label: 'Adult: 19+ years', backendKey: 'adult_19_plus' },
    { value: 'aged_65_plus', label: 'Aged: 65+ years', backendKey: 'aged_65_plus' }
  ];

  const PUBLICATION_DATE_OPTIONS = [
    { value: 'within_1y', label: '1 year', backendKey: 'within_1y', type: '1_year' },
    { value: 'within_5y', label: '5 years', backendKey: 'within_5y', type: '5_years' },
    { value: 'within_10y', label: '10 years', backendKey: 'within_10y', type: '10_years' }
  ];

  const getInitialFilters = () => ({
    source_type: ['PM', 'CTG'],
    article_type: [],
    species: [],
    age: [],
    publication_date: {
      type: null,
      from_year: '',
      to_year: ''
    },
    pmc_open_access: true,  // Default to checked
    ctg_has_results: false,
    ctg_status: []
  });

  // Use external filters if provided, otherwise use local state
  const [localFilters, setLocalFilters] = useState(getInitialFilters());
  const filters = externalFilters || localFilters;
  const setFilters = setExternalFilters || setLocalFilters;

  const getDynamicCount = (category, value) => {
    if (!filterStats) return { pm: 0, ctg: 0, total: 0 };
    
    // For data_source, return totals directly
    if (category === 'data_source') {
      if (value === 'pubmed') {
        const pmTotal = filterStats.data_source?.pubmed || 0;
        return { pm: pmTotal, ctg: 0, total: pmTotal };
      }
      if (value === 'clinicaltrials_gov') {
        const ctgTotal = filterStats.data_source?.clinicaltrials_gov || 0;
        return { pm: 0, ctg: ctgTotal, total: ctgTotal };
      }
    }
    
    // For additional_filters (species, age), navigate nested structure
    if (category === 'additional_filters') {
      const speciesData = filterStats.additional_filters?.species?.[value];
      if (speciesData && typeof speciesData === 'object' && 'pm' in speciesData) {
        return {
          pm: speciesData.pm || 0,
          ctg: speciesData.ctg || 0,
          total: speciesData.total || 0
        };
      }
      
      const ageData = filterStats.additional_filters?.age?.[value];
      if (ageData && typeof ageData === 'object' && 'pm' in ageData) {
        return {
          pm: ageData.pm || 0,
          ctg: ageData.ctg || 0,
          total: ageData.total || 0
        };
      }
    }
    
    // For other categories with nested pm/ctg/total structure
    const itemData = filterStats[category]?.[value];
    if (itemData && typeof itemData === 'object' && 'pm' in itemData) {
      return {
        pm: itemData.pm || 0,
        ctg: itemData.ctg || 0,
        total: itemData.total || 0
      };
    }
    
    // Fallback for unexpected structure
    return { pm: 0, ctg: 0, total: 0 };
  };

  const handleSourceTypeChange = (source) => {
    setFilters(prev => {
      const currentSources = prev.source_type || [];
      const newSources = currentSources.includes(source)
        ? currentSources.filter(s => s !== source)
        : [...currentSources, source];
      return { ...prev, source_type: newSources };
    });
  };

  const handleCheckboxChange = (category, value) => {
    setFilters(prev => {
      const current = prev[category] || [];
      const updated = current.includes(value)
        ? current.filter(v => v !== value)
        : [...current, value];
      return { ...prev, [category]: updated };
    });
  };

  const handlePublicationDateChange = (type) => {
    setFilters(prev => ({
      ...prev,
      publication_date: {
        ...(prev.publication_date || {}),
        type: prev.publication_date?.type === type ? null : type,
        from_year: type === 'custom' ? (prev.publication_date?.from_year || '') : '',
        to_year: type === 'custom' ? (prev.publication_date?.to_year || '') : ''
      }
    }));
  };

  const handleCustomYearChange = (field, value) => {
    setFilters(prev => ({
      ...prev,
      publication_date: {
        ...(prev.publication_date || {}),
        [field]: value
      }
    }));
  };

  const handleApply = () => {
    filterLogger.debug('[PubMedFilters] Applying filters:', filters);
    onApplyFilters({
      ...filters,
      search_key: searchKey
    });
  };

  const handleClear = () => {
    setFilters(getInitialFilters());
  };

  const handleClearCategory = (category) => {
    if (category === 'publication_date') {
      setFilters(prev => ({
        ...prev,
        publication_date: { type: null, from_year: '', to_year: '' }
      }));
    } else {
      setFilters(prev => ({
        ...prev,
        [category]: Array.isArray(prev[category]) ? [] : null
      }));
    }
  };

  return (
    <div className="w-full space-y-4">
      <div className="bg-custom-bg-soft rounded-lg p-3 border border-custom-border">
        <h4 className="font-semibold mb-2 text-custom-text text-sm">Data Source</h4>
        <div className="space-y-2">
          {[
            { value: 'PM', label: 'PubMed', key: 'pubmed', color: 'text-blue-700', bgColor: 'bg-blue-100' },
            { value: 'CTG', label: 'ClinicalTrials.gov', key: 'clinicaltrials_gov', color: 'text-green-700', bgColor: 'bg-green-100' }
          ].map(source => {
            const count = getDynamicCount('data_source', source.key);
            return (
              <label key={source.value} className="flex items-center gap-2 cursor-pointer text-sm">
                <input
                  type="checkbox"
                  checked={filters.source_type?.includes(source.value) || false}
                  // checked={filters.source_type.includes(source.value)}
                  onChange={() => handleSourceTypeChange(source.value)}
                  className="accent-custom-blue w-3 h-3 rounded border-gray-300"
                />
                <span className="text-custom-text font-medium flex-1">{source.label}</span>
                <span className={`px-2 py-0.5 rounded-full ${source.bgColor} ${source.color} text-xs font-bold`}>
                  {count.total}
                </span>
              </label>
            );
          })}
        </div>
      </div>

      <div className="bg-custom-bg-soft rounded-lg p-3 border border-custom-border">
        <div className="flex items-center justify-between mb-2">
          <h4 className="font-semibold text-custom-text text-sm">Publication Date</h4>
          {filters.publication_date?.type && (
            <button 
              onClick={() => handleClearCategory('publication_date')}
              className="text-xs text-gray-600 hover:text-custom-blue"
            >
              Clear
            </button>
          )}
        </div>
        <div className="space-y-2">
          {PUBLICATION_DATE_OPTIONS.map(option => {
            const count = getDynamicCount('publication_date', option.value);
            return (
              <label key={option.value} className="flex items-center gap-2 cursor-pointer text-sm">
                <input
                  type="radio"
                  name="publication_date"
                  checked={filters.publication_date?.type === option.type}
                  onChange={() => handlePublicationDateChange(option.type)}
                  className="accent-custom-blue"
                />
                <span className="text-custom-text flex-1">{option.label}</span>
                <div className="flex gap-1">
                  {count.pm > 0 && (
                    <span className="px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700 text-xs font-semibold">
                      {count.pm}
                    </span>
                  )}
                  {count.ctg > 0 && (
                    <span className="px-1.5 py-0.5 rounded-full bg-green-100 text-green-700 text-xs font-semibold">
                      {count.ctg}
                    </span>
                  )}
                  {count.total === 0 && (
                    <span className="px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-600 text-xs font-semibold">
                      0
                    </span>
                  )}
                </div>
              </label>
            );
          })}
          
          {/* Custom Date Range */}
          <div className="pt-2 border-t border-custom-border">
            <label className="flex items-center gap-2 cursor-pointer text-sm mb-2">
              <input
                type="radio"
                name="publication_date"
                checked={filters.publication_date?.type === 'custom'}
                onChange={() => handlePublicationDateChange('custom')}
                className="accent-custom-blue"
              />
              <span className="text-custom-text flex-1">Custom Range</span>
            </label>
            {filters.publication_date?.type === 'custom' && (
              <div className="ml-6 space-y-2">
                <div className="flex items-center gap-2">
                  <label className="text-xs text-custom-text-subtle w-16">From:</label>
                  <input
                    type="number"
                    placeholder="Year"
                    min="1900"
                    max={new Date().getFullYear()}
                    value={filters.publication_date?.from_year || ''}
                    onChange={(e) => handleCustomYearChange('from_year', e.target.value)}
                    className="flex-1 px-2 py-1 text-xs border border-custom-border rounded focus:outline-none focus:ring-1 focus:ring-custom-blue"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <label className="text-xs text-custom-text-subtle w-16">To:</label>
                  <input
                    type="number"
                    placeholder="Year"
                    min="1900"
                    max={new Date().getFullYear()}
                    value={filters.publication_date?.to_year || ''}
                    onChange={(e) => handleCustomYearChange('to_year', e.target.value)}
                    className="flex-1 px-2 py-1 text-xs border border-custom-border rounded focus:outline-none focus:ring-1 focus:ring-custom-blue"
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Phase Filters */}
      <div className="bg-custom-bg-soft rounded-lg p-3 border border-custom-border">
        <div className="flex items-center justify-between mb-2">
          <h4 className="font-semibold text-custom-text text-sm">Phase</h4>
          {filters.article_type && filters.article_type.some(type => PHASE_OPTIONS.some(opt => opt.value === type)) && (
            <button 
              onClick={() => {
                const phaseValues = PHASE_OPTIONS.map(opt => opt.value);
                setFilters(prev => ({
                  ...prev,
                  article_type: (prev.article_type || []).filter(type => !phaseValues.includes(type))
                }));
              }}
              className="text-xs text-gray-600 hover:text-custom-blue"
            >
              Clear
            </button>
          )}
        </div>
        <div className="space-y-1">
          {PHASE_OPTIONS.map(option => {
            const count = getDynamicCount('article_type', option.value);
            return (
              <label key={option.value} className="flex items-center gap-2 cursor-pointer text-sm">
                <input
                  type="checkbox"
                  checked={filters.article_type?.includes(option.value) || false}
                  onChange={() => handleCheckboxChange('article_type', option.value)}
                  className="accent-custom-blue w-3 h-3 rounded border-gray-300"
                />
                <span className="text-custom-text flex-1">{option.label}</span>
                <div className="flex gap-1">
                  {count.pm > 0 && (
                    <span className="px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700 text-xs font-semibold">
                      {count.pm}
                    </span>
                  )}
                  {count.ctg > 0 && (
                    <span className="px-1.5 py-0.5 rounded-full bg-green-100 text-green-700 text-xs font-semibold">
                      {count.ctg}
                    </span>
                  )}
                  {count.total === 0 && (
                    <span className="px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-600 text-xs font-semibold">
                      0
                    </span>
                  )}
                </div>
              </label>
            );
          })}
        </div>
      </div>

      {/* Study Type Filters */}
      <div className="bg-custom-bg-soft rounded-lg p-3 border border-custom-border">
        <div className="flex items-center justify-between mb-2">
          <h4 className="font-semibold text-custom-text text-sm">Study Type</h4>
          {filters.article_type && filters.article_type.some(type => STUDY_TYPE_OPTIONS.some(opt => opt.value === type)) && (
            <button 
              onClick={() => {
                const studyTypeValues = STUDY_TYPE_OPTIONS.map(opt => opt.value);
                setFilters(prev => ({
                  ...prev,
                  article_type: (prev.article_type || []).filter(type => !studyTypeValues.includes(type))
                }));
              }}
              className="text-xs text-gray-600 hover:text-custom-blue"
            >
              Clear
            </button>
          )}
        </div>
        <div className="space-y-1">
          {STUDY_TYPE_OPTIONS.map(option => {
            const count = getDynamicCount('article_type', option.value);
            return (
              <label key={option.value} className="flex items-center gap-2 cursor-pointer text-sm">
                <input
                  type="checkbox"
                  checked={filters.article_type?.includes(option.value) || false}
                  onChange={() => handleCheckboxChange('article_type', option.value)}
                  className="accent-custom-blue w-3 h-3 rounded border-gray-300"
                />
                <span className="text-custom-text flex-1">{option.label}</span>
                <div className="flex gap-1">
                  {count.pm > 0 && (
                    <span className="px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700 text-xs font-semibold">
                      {count.pm}
                    </span>
                  )}
                  {count.ctg > 0 && (
                    <span className="px-1.5 py-0.5 rounded-full bg-green-100 text-green-700 text-xs font-semibold">
                      {count.ctg}
                    </span>
                  )}
                  {count.total === 0 && (
                    <span className="px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-600 text-xs font-semibold">
                      0
                    </span>
                  )}
                </div>
              </label>
            );
          })}
        </div>
      </div>

      {/* Age Filters */}
      <div className="bg-custom-bg-soft rounded-lg p-3 border border-custom-border">
        <div className="flex items-center justify-between mb-2">
          <h4 className="font-semibold text-custom-text text-sm">Age</h4>
          {filters.age && filters.age.length > 0 && (
            <button 
              onClick={() => handleClearCategory('age')}
              className="text-xs text-gray-600 hover:text-custom-blue"
            >
              Clear
            </button>
          )}
        </div>
        <div className="space-y-1">
          {AGE_OPTIONS.map(option => {
            const count = getDynamicCount('additional_filters', option.value);
            return (
              <label key={option.value} className="flex items-center gap-2 cursor-pointer text-sm">
                <input
                  type="checkbox"
                  checked={filters.age?.includes(option.value) || false}
                  onChange={() => handleCheckboxChange('age', option.value)}
                  className="accent-custom-blue w-3 h-3 rounded border-gray-300"
                />
                <span className="text-custom-text flex-1">{option.label}</span>
                <div className="flex gap-1">
                  {count.pm > 0 && (
                    <span className="px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700 text-xs font-semibold">
                      {count.pm}
                    </span>
                  )}
                  {count.ctg > 0 && (
                    <span className="px-1.5 py-0.5 rounded-full bg-green-100 text-green-700 text-xs font-semibold">
                      {count.ctg}
                    </span>
                  )}
                  {count.total === 0 && (
                    <span className="px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-600 text-xs font-semibold">
                      0
                    </span>
                  )}
                </div>
              </label>
            );
          })}
        </div>
      </div>

      {/* PubMed-Only Filters */}
      <div className="bg-custom-bg-soft rounded-lg p-3 border border-custom-border">
        <div className="flex items-center justify-between mb-2">
          <h4 className="font-semibold text-custom-text text-sm flex items-center gap-2">
            PubMed Only
            {/* <span className="px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700 text-xs font-semibold">PM</span> */}
          </h4>
          {(filters.article_type && filters.article_type.some(type => PUBMED_ONLY_ARTICLE_TYPES.some(opt => opt.value === type)) || 
            filters.species && filters.species.length > 0 ||
            !filters.pmc_open_access) && (
            <button 
              onClick={() => {
                const pubmedOnlyArticleValues = PUBMED_ONLY_ARTICLE_TYPES.map(opt => opt.value);
                setFilters(prev => ({
                  ...prev,
                  article_type: (prev.article_type || []).filter(type => !pubmedOnlyArticleValues.includes(type)),
                  species: [],
                  pmc_open_access: true
                }));
              }}
              className="text-xs text-gray-600 hover:text-custom-blue"
            >
              Clear
            </button>
          )}
        </div>
        
        {/* PMC Open Access */}
        <div className="mb-3">
          <label className="flex items-center gap-2 cursor-pointer text-sm">
            <input
              type="checkbox"
              checked={filters.pmc_open_access !== undefined ? filters.pmc_open_access : true}
              onChange={() => setFilters(prev => ({ ...prev, pmc_open_access: !prev.pmc_open_access }))}
              className="accent-custom-blue w-3 h-3 rounded border-gray-300"
            />
            <span className="text-custom-text flex-1">PMC Open Access</span>
          </label>
        </div>
        
        {/* Article Types */}
        <div className="mb-3">
          <h5 className="font-medium text-custom-text text-xs mb-2">Article Types</h5>
          <div className="space-y-1">
            {PUBMED_ONLY_ARTICLE_TYPES.map(option => {
              const count = getDynamicCount('article_type', option.value);
              return (
                <label key={option.value} className="flex items-center gap-2 cursor-pointer text-sm">
                  <input
                    type="checkbox"
                    checked={filters.article_type?.includes(option.value) || false}
                    onChange={() => handleCheckboxChange('article_type', option.value)}
                    className="accent-custom-blue w-3 h-3 rounded border-gray-300"
                  />
                  <span className="text-custom-text flex-1">{option.label}</span>
                  <div className="flex gap-1">
                    {count.pm > 0 && (
                      <span className="px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700 text-xs font-semibold">
                        {count.pm}
                      </span>
                    )}
                    {count.total === 0 && (
                      <span className="px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-600 text-xs font-semibold">
                        0
                      </span>
                    )}
                  </div>
                </label>
              );
            })}
          </div>
        </div>

        {/* Species */}
        <div className="mb-0">
          <h5 className="font-medium text-custom-text text-xs mb-2">Species</h5>
          <div className="space-y-1">
            {PUBMED_ONLY_SPECIES.map(option => {
              const count = getDynamicCount('additional_filters', option.value);
              return (
                <label key={option.value} className="flex items-center gap-2 cursor-pointer text-sm">
                  <input
                    type="checkbox"
                    checked={filters.species?.includes(option.value) || false}
                    onChange={() => handleCheckboxChange('species', option.value)}
                    className="accent-custom-blue w-3 h-3 rounded border-gray-300"
                  />
                  <span className="text-custom-text flex-1">{option.label}</span>
                  <div className="flex gap-1">
                    {count.pm > 0 && (
                      <span className="px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700 text-xs font-semibold">
                        {count.pm}
                      </span>
                    )}
                    {count.total === 0 && (
                      <span className="px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-600 text-xs font-semibold">
                        0
                      </span>
                    )}
                  </div>
                </label>
              );
            })}
          </div>
        </div>
      </div>

      {/* CTG-Only Filters */}
      <div className="bg-custom-bg-soft rounded-lg p-3 border border-custom-border">
        <div className="flex items-center justify-between mb-2">
          <h4 className="font-semibold text-custom-text text-sm flex items-center gap-2">
            CTG Only
            {/* <span className="px-1.5 py-0.5 rounded-full bg-green-100 text-green-700 text-xs font-semibold">CTG</span> */}
          </h4>
          {(filters.ctg_has_results || (filters.ctg_status && filters.ctg_status.length > 0)) && (
            <button 
              onClick={() => {
                setFilters(prev => ({
                  ...prev,
                  ctg_has_results: false,
                  ctg_status: []
                }));
              }}
              className="text-xs text-gray-600 hover:text-custom-blue"
            >
              Clear
            </button>
          )}
        </div>
        
        {/* Has Results */}
        <div className="mb-3">
          {/* <h5 className="font-medium text-custom-text text-xs mb-2">Has Results</h5> */}
          <label className="flex items-center gap-2 cursor-pointer text-sm">
            <input
              type="checkbox"
              checked={filters.ctg_has_results || false}
              onChange={() => setFilters(prev => ({ ...prev, ctg_has_results: !prev.ctg_has_results }))}
              className="accent-custom-blue w-3 h-3 rounded border-gray-300"
            />
            <span className="text-custom-text flex-1">Has Results</span>
            <span className={`px-1.5 py-0.5 rounded-full text-xs font-semibold ${
              (filterStats?.ctg_filters?.has_results || 0) > 0 
                ? 'bg-green-100 text-green-700' 
                : 'bg-gray-100 text-gray-600'
            }`}>
              {filterStats?.ctg_filters?.has_results || 0}
            </span>
          </label>
        </div>

        {/* Status */}
        <div className="mb-0">
          <h5 className="font-medium text-custom-text text-xs mb-2">Status</h5>
          <div className="space-y-1">
            {[
              { value: 'RECRUITING', label: 'Recruiting' },
              { value: 'COMPLETED', label: 'Completed' }
            ].map(option => {
              const count = filterStats?.ctg_filters?.status?.[option.value.toLowerCase()] || 0;
              return (
                <label key={option.value} className="flex items-center gap-2 cursor-pointer text-sm">
                  <input
                    type="checkbox"
                    checked={filters.ctg_status?.includes(option.value) || false}
                    onChange={() => handleCheckboxChange('ctg_status', option.value)}
                    className="accent-custom-blue w-3 h-3 rounded border-gray-300"
                  />
                  <span className="text-custom-text flex-1">{option.label}</span>
                  <span className={`px-1.5 py-0.5 rounded-full text-xs font-semibold ${
                    count > 0 
                      ? 'bg-green-100 text-green-700' 
                      : 'bg-gray-100 text-gray-600'
                  }`}>
                    {count}
                  </span>
                </label>
              );
            })}
          </div>
        </div>
      </div>

      {/* CTG-Only Filters - Placeholder for future */}
      {CTG_ONLY_OPTIONS.length > 0 && (
        <div className="bg-custom-bg-soft rounded-lg p-3 border border-custom-border">
          <div className="flex items-center justify-between mb-2">
            <h4 className="font-semibold text-custom-text text-sm flex items-center gap-2">
              ClinicalTrials.gov-Only Filters
              <span className="px-1.5 py-0.5 rounded-full bg-green-100 text-green-700 text-xs font-semibold">CTG</span>
            </h4>
          </div>
          <div className="space-y-1">
            {CTG_ONLY_OPTIONS.map(option => {
              const count = getDynamicCount('article_type', option.value);
              return (
                <label key={option.value} className="flex items-center gap-2 cursor-pointer text-sm">
                  <input
                    type="checkbox"
                    checked={filters.article_type?.includes(option.value) || false}
                    // checked={filters.article_type.includes(option.value)}
                    onChange={() => handleCheckboxChange('article_type', option.value)}
                    className="accent-custom-blue w-3 h-3 rounded border-gray-300"
                  />
                  <span className="text-custom-text flex-1">{option.label}</span>
                  <div className="flex gap-1">
                    {count.ctg > 0 && (
                      <span className="px-1.5 py-0.5 rounded-full bg-green-100 text-green-700 text-xs font-semibold">
                        {count.ctg}
                      </span>
                    )}
                    {count.total === 0 && (
                      <span className="px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-600 text-xs font-semibold">
                        0
                      </span>
                    )}
                  </div>
                </label>
              );
            })}
          </div>
        </div>
      )}

      <div className="flex gap-2 pt-2 border-t border-gray-200">
        <button
          onClick={handleApply}
          disabled={isLoading}
          className="flex-1 px-3 py-2 bg-custom-blue text-white rounded-lg font-semibold text-sm shadow-sm hover:bg-custom-blue-hover disabled:opacity-50 transition"
        >
          {isLoading ? 'Applying...' : 'Apply Filters'}
        </button>
        <button
          onClick={handleClear}
          disabled={isLoading}
          className="px-3 py-2 border border-custom-border rounded-lg font-semibold text-custom-text bg-white hover:bg-gray-50 disabled:opacity-50 transition text-sm"
        >
          Clear All
        </button>
      </div>
    </div>
  );
};

PubMedFiltersSidebar.propTypes = {
  onApplyFilters: PropTypes.func.isRequired,
  isLoading: PropTypes.bool,
  searchKey: PropTypes.string,
  filterStats: PropTypes.object,
  filters: PropTypes.object,
  setFilters: PropTypes.func
};

export default PubMedFiltersSidebar;
