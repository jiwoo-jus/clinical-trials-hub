import React from 'react';
import PropTypes from 'prop-types';

const fieldLabels = {
  cond: 'Condition',
  intr: 'Intervention',
  other_term: 'Other Terms'
};

export const FilterPanel = ({ filters, setFilters }) => {
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
                placeholder={`${field === 'cond' ? 'Diabetes' : field === 'intr' ? 'Insulin' : 'RCT'}`}
                className="mt-1 block w-full border light:border-primary-12 rounded-2xl px-4 py-2 text-sm light:shadow-splash-chatpgpt-input"
              />
            </div>
          ))}
        </div>
        <div className="mt-6 border-t pt-4">
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
                placeholder="Myelofibrosis AND Randomized Controlled Trial[PT])"
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
                placeholder='Hypertension AND ("Cleveland, Ohio") AND recruiting'
                className="mt-1 block w-full border light:border-primary-12 rounded-2xl px-4 py-2 text-sm light:shadow-splash-chatpgpt-input"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

FilterPanel.propTypes = {
  filters: PropTypes.object.isRequired,
  setFilters: PropTypes.func.isRequired,
};
