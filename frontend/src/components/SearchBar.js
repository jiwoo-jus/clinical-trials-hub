import React, { useState, useEffect, useRef } from 'react';
import { Search } from 'lucide-react';
import PropTypes from 'prop-types';

export const SearchBar = ({ query, setQuery, onSubmit, loading = false, filters = {}, patientMode = false }) => {
  const placeholderTexts = !patientMode ? [
    "Diabetes insulin child",
    "Elderly Alzheimer's"
  ] : [
    "ADHD trials for 15 year olds in Ohio",
    "Seeking insulin based trials for elderly female diabetes patient"
  ] ;

  const [currentIdx, setCurrentIdx] = useState(0);
  const textareaRef = useRef(null);

  // Helper function to check if search is possible
  const canSearch = () => {
    // Check if main query has content
    if (query && query.trim()) {
      return true;
    }
    
    // Check if any of the filter fields have values
    const searchableFields = ['cond', 'intr', 'other_term', 'pubmed_query', 'ctg_query'];
    return searchableFields.some(field => filters[field] && filters[field].trim());
  };

  // change placeholder text every 3 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentIdx((prev) => (prev + 1) % placeholderTexts.length);
    }, 3000);
    return () => clearInterval(interval);
  }, [placeholderTexts.length]);

  // Enter key submits the form if Shift is not pressed, otherwise it allows line breaks
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey && canSearch()) {
      e.preventDefault();
      onSubmit();
    }
  };

  // adjust textarea height based on content
  const handleChange = (e) => {
    setQuery(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px';
    }
  };

  return (
    <div className="relative z-40 mx-auto w-full max-w-[768px]">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (canSearch()) {
            onSubmit();
          }
        }}
        className="relative"
      >
        <label
          className="
            relative flex w-full cursor-text flex-col overflow-hidden
            rounded-2xl px-4 py-3
            light:border-primary-12 dark:bg-primary-4 light:bg-secondary-100
            light:shadow-splash-chatpgpt-input
          "
        >
          <div className="sr-only">Search</div>

          {/* appearing placeholder text when query is empty */}
          {!query && (
            <div className="absolute left-4 top-3 text-custom-text-subtle pointer-events-none transition-opacity duration-300 truncate">
              {placeholderTexts[currentIdx]}
            </div>
          )}

          <textarea
            ref={textareaRef}
            rows="1"
            placeholder=" "
            value={query}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            disabled={loading}
            className="
              relative w-full pr-12 bg-transparent text-base leading-relaxed
              resize-none overflow-hidden focus:outline-none
              disabled:opacity-50 disabled:cursor-not-allowed
            "
          />

          <div className="absolute bottom-3 right-3 flex justify-end">
            <button
              type="submit"
              disabled={loading || !canSearch()}
              aria-label="Send search query"
              className="
                bg-primary-100 text-secondary-100 disabled:bg-primary-4 disabled:text-primary-44
                relative h-9 w-9 rounded-full p-0 transition-colors hover:opacity-70 disabled:hover:opacity-100
                disabled:cursor-not-allowed
              "
            >
              <Search size={16} />
            </button>
          </div>
        </label>
      </form>
    </div>
  );
};

SearchBar.propTypes = {
  query: PropTypes.string.isRequired,
  setQuery: PropTypes.func.isRequired,
  onSubmit: PropTypes.func.isRequired,
  loading: PropTypes.bool,
  filters: PropTypes.object,
  patientMode: PropTypes.bool
};
