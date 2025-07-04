// import { Filter } from 'lucide-react';
import PropTypes from 'prop-types';
import React from 'react';

// Add a mapping for field names to display labels
const fieldLabels = {
  cond: 'Condition',
  intr: 'Intervention',
  other_term: 'Other Terms'
};

// Helper function to get source badge color - commented out for potential future use
/* const getSourceBadgeColor = (source) => {
  switch (source) {
    case 'PubMed':
      return 'bg-blue-100 text-blue-800 border-blue-200';
    case 'CTG':
      return 'bg-green-100 text-green-800 border-green-200';
    case 'CTH':
      return 'bg-purple-100 text-purple-800 border-purple-200';
    default:
      return 'bg-gray-100 text-gray-800 border-gray-200';
  }
}; */

// Source badges for each filter - commented out for potential future use
/* const getFilterSources = (name) => {
  const sourceMap = {
    cond: ['PubMed', 'CTG'],
    intr: ['PubMed', 'CTG'],
    other_term: ['PubMed', 'CTG'],
    journal: ['PubMed'],
    sex: ['PubMed', 'CTH'],
    age: ['PubMed', 'CTH'],
    studyType: ['CTG'],
    sponsor: ['CTH'],
    location: ['CTH'],
    status: ['CTH']
  };
  return sourceMap[name] || [];
}; */

export const FilterPanel = ({ filters, setFilters }) => {
  // showMore feature removed (code retained for possible future reactivation)
  // const [showMore, setShowMore] = React.useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFilters({
      ...filters,
      [name]: value === '' ? null : value,
    });
  };

  return (
    <div className="w-full max-w-7xl mx-auto px-4">
      <div className="w-full bg-white light:border-primary-12 light:bg-secondary-100 rounded-2xl light:shadow-splash-chatpgpt-input p-6 mb-6 border">
        {/* <div className="flex items-center justify-between mb-4"> */}
          {/* <h2 className="text-lg font-semibold flex items-center gap-2">
            <Filter size={18} className="text-primary-100" />
            Search Filters
          </h2> */}
          {/* Advanced Filter button hide */}
          {/* <button
            onClick={() => setShowMore(!showMore)}
            className="text-sm text-primary-100 hover:underline flex items-center gap-1"
          >
            <Info size={14} />
            {showMore ? 'Hide Advanced Filters' : 'Show Advanced Filters'}
          </button> */}
        {/* </div> */}

        {/* Legend */}
        {/* <div className="mb-4 p-3 bg-gray-50 rounded-lg">
          <h3 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-1">
            <Info size={14} />
            Filter Application
          </h3>
          <div className="flex flex-wrap gap-2 text-xs">
            <span className={`inline-flex items-center px-2 py-1 rounded-full font-medium border ${getSourceBadgeColor('PubMed')}`}>
              PubMed API
            </span>
            <span className={`inline-flex items-center px-2 py-1 rounded-full font-medium border ${getSourceBadgeColor('CTG')}`}>
              CTG API
            </span>
            <span className={`inline-flex items-center px-2 py-1 rounded-full font-medium border ${getSourceBadgeColor('CTH')}`}>
              CTH Filter
            </span>
          </div>
        </div> */}

        {/* Basic Filters */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {['cond', 'intr', 'other_term'].map((field, idx) => (
            <div key={idx}>
              <label className="block text-sm font-medium text-primary-100 capitalize">
                {fieldLabels[field] || field.replace('_', ' ')}
              </label>
              <input
                type="text"
                name={field}
                value={filters[field] || ''}
                onChange={handleChange}
                placeholder={`e.g., ${field === 'cond' ? 'Diabetes' : field === 'intr' ? 'Insulin' : 'RCT'}`}
                className="mt-1 block w-full border light:border-primary-12 rounded-2xl px-4 py-2 text-sm light:shadow-splash-chatpgpt-input"
              />
            </div>
          ))}
        </div>

        {/* Direct Query Filters */}
        <div className="mt-6 border-t pt-4">
          {/* <h3 className="text-md font-medium text-primary-100 mb-3">Direct Query Search</h3> */}
          {/* <p className="text-xs text-gray-500 mb-3">
            When using direct queries below, all other filters and search values will be ignored. The query will be sent directly to the respective data source.
          </p> */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-primary-100">
                PubMed Query
              </label>
              <input
                type="text"
                name="pubmed_query"
                value={filters.pubmed_query || ''}
                onChange={handleChange}
                placeholder="e.g., Myelofibrosis AND (Clinical Trial[PT] OR Randomized Controlled Trial[PT])"
                className="mt-1 block w-full border light:border-primary-12 rounded-2xl px-4 py-2 text-sm light:shadow-splash-chatpgpt-input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-primary-100">
                CTG Query
              </label>
              <input
                type="text"
                name="ctg_query"
                value={filters.ctg_query || ''}
                onChange={handleChange}
                placeholder='e.g., Hypertension AND recruiting AND ("Cleveland, Ohio" OR "Cincinnati, Ohio")'
                className="mt-1 block w-full border light:border-primary-12 rounded-2xl px-4 py-2 text-sm light:shadow-splash-chatpgpt-input"
              />
            </div>
          </div>
        </div>

        {/* Advanced Filters - commented out for potential future use */}
        {/* {showMore && (
          <div className="mt-6">
            <h3 className="text-md font-medium text-primary-100 mb-3 border-t pt-4">Advanced Filters</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[
                ['journal', 'e.g., BMJ Open'],
                ['sex', ''],
                ['age', ''],
                ['studyType', ''],
                ['sponsor', 'e.g., NIH'],
                ['location', 'e.g., Columbus, OH'],
                ['status', 'e.g., Completed']
              ].map(([name, placeholder], idx) => (
                <div key={idx}>
                  <label className="block text-sm font-medium text-primary-100 capitalize">
                    {name.replace(/([A-Z])/g, ' $1')}
                  </label>
                  {['sex', 'age', 'studyType'].includes(name) ? (
                    <select
                      name={name}
                      value={filters[name] || ''}
                      onChange={handleChange}
                      className="mt-1 block w-full border light:border-primary-12 rounded-2xl px-4 py-2 text-sm light:shadow-splash-chatpgpt-input"
                    >
                      <option value="">Any</option>
                      {name === 'sex' && (
                        <>
                          <option value="Male">Male</option>
                          <option value="Female">Female</option>
                        </>
                      )}
                      {name === 'age' && (
                        <>
                          <option value="child">Child</option>
                          <option value="adult">Adult</option>
                          <option value="older">Older</option>
                        </>
                      )}
                      {name === 'studyType' && (
                        <option value="int obs">Interventional/Observational</option>
                      )}
                    </select>
                  ) : (
                    <input
                      type="text"
                      name={name}
                      value={filters[name] || ''}
                      onChange={handleChange}
                      placeholder={placeholder}
                      className="mt-1 block w-full border light:border-primary-12 rounded-2xl px-4 py-2 text-sm light:shadow-splash-chatpgpt-input"
                    />
                  )}
                  <div className="mt-1 flex flex-wrap gap-1">
                    {getFilterSources(name).map((source, sourceIdx) => (
                      <span
                        key={sourceIdx}
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${getSourceBadgeColor(source)}`}
                      >
                        {source}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )} */}
      </div>
    </div>
  );
};

FilterPanel.propTypes = {
  filters: PropTypes.object.isRequired,
  setFilters: PropTypes.func.isRequired,
};
