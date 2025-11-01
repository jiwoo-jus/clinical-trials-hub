// src/components/SearchHistorySidebar.js

import React from 'react';
import PropTypes from 'prop-types';

const labelMap = {
  cond: "Condition",
  intr: "Intervention",
  other_term: "Other Term",
  journal: "Journal",
  sex: "Sex",
  age: "Age Group",
  studyType: "Study Type",
  sponsor: "Sponsor",
  location: "Location",
  status: "Status",
  sources: "Sources"
};

const SearchHistorySidebar = ({ history, onSelect, isOpen, toggleSidebar, sidebarWidth }) => {
  return (
    <div
      className="bg-white shadow-md p-2 overflow-auto sticky top-0"
      style={{ width: isOpen ? sidebarWidth : "2rem", transition: "width 0.3s" }}
    >
      <button onClick={toggleSidebar} className="text-sm text-blue-500 focus:outline-none">
        {isOpen ? "<<" : ">>"}
      </button>
      {isOpen && (
        <div className="mt-2 text-sm break-words">
          <h3 className="font-semibold mb-2">Search History</h3>
          {history.length === 0 ? (
            <p className="text-custom-text-subtle">No history yet.</p>
          ) : (
            <ul>
              {history.map((item, index) => (
                <li key={index} className="mb-2 border-b pb-1">
                  <button
                    onClick={() => onSelect(item)}
                    className="block text-left w-full text-custom-text hover:bg-custom-input-bg rounded p-1"
                  >
                    {Object.entries(item).map(([key, value]) => {
                      if (!value) return null;
                      return (
                        <div key={key}>
                          <span className="font-bold">{labelMap[key] || key}:</span>{" "}
                          {Array.isArray(value) ? value.join(", ") : value}
                        </div>
                      );
                    })}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
};

SearchHistorySidebar.propTypes = {
  history: PropTypes.arrayOf(
    PropTypes.shape({
      cond: PropTypes.string,
      intr: PropTypes.string,
      other_term: PropTypes.string,
      journal: PropTypes.string,
      sex: PropTypes.string,
      age: PropTypes.string,
      studyType: PropTypes.string,
      sponsor: PropTypes.string,
      location: PropTypes.string,
      status: PropTypes.string,
      sources: PropTypes.arrayOf(PropTypes.string)
    })
  ).isRequired,
  onSelect: PropTypes.func.isRequired,
  isOpen: PropTypes.bool.isRequired,
  toggleSidebar: PropTypes.func.isRequired,
  sidebarWidth: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired
};

export default SearchHistorySidebar;
