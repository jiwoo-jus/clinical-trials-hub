import React, { useState, useCallback, useEffect } from 'react';
import PropTypes from 'prop-types';
import { searchClinicalTrials } from '../api/searchApi';
import { ChevronDown } from 'lucide-react';

const SESSION_KEY = 'searchState';

const QueryList = ({ dynamicQueries, handleQuerySelect, baseResults }) => {
  const [showMore, setShowMore] = useState(false);
  const [results, setResults] = useState({});
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState(null);
  const [resultSelected, setResultSelected] = useState(false);
  const [queryResults, setQueryResults] = useState([]);

  // Query builder state
  const [currentTerm, setCurrentTerm] = useState("");
  const [queryString, setQueryString] = useState("");

  // Collect all terms from dynamic queries
  const allTerms = dynamicQueries?.queries?.reduce((acc, q) => {
  if (q.terms?.length) {
    acc[q.name] = q.terms;
  }
  return acc;
}, {}) || {};


  // Add term to query string
const addToQuery = (term, op = "AND", nest = false) => {
  let newQuery = queryString.trim();
  
  // Format term with field if not "All Fields"
  let formattedTerm = term;

  if (newQuery === "") {
    // First term - just add it
    newQuery = formattedTerm;
  } else if (nest) {
    // Nesting: wrap the existing query in parentheses, THEN add operator and new term
    if (op === "NOT") {
      newQuery = `(${newQuery}) NOT ${formattedTerm}`;
    } else {
      newQuery = `(${newQuery}) ${op} ${formattedTerm}`;
    }
  } else {
    // Append: just add to the end with operator
    if (op === "NOT") {
      newQuery = `${newQuery} NOT ${formattedTerm}`;
    } else {
      newQuery = `${newQuery} ${op} ${formattedTerm}`;
    }
  }
  setQueryString(newQuery);
  setCurrentTerm("");
};

  // Handle term click from list
  const handleTermClick = (term) => {
    setCurrentTerm(term);
  };

  // Handle manual query string edit
  const handleQueryEdit = (e) => {
    setQueryString(e.target.value);
  };

  // Clear query
  const clearQuery = () => {
    setQueryString("");
    setCurrentTerm("");
  };

  // Handle advanced search
  const handleAdvancedSearch = async () => {
    if (!queryString.trim()) return;
    
    setLoading(true);
    setResults({});
    
    const params = {
      query: queryString,
      isRefined: true,
      refinedQuery: {
        combined_query: queryString,
      },
    };

    try {
      const res = await searchClinicalTrials(params);
      setResults({
        search_key: res.search_key,
        results: Array.isArray(res.results) ? res.results : [],
        counts: res.counts || {
          total: 0,
          merged: 0,
          pm_only: 0,
          ctg_only: 0,
        },
        total: res.total || 0,
        totalPages: res.totalPages || 1,
        filter_stats: res.filter_stats,
        refinedQuery: res.refinedQuery,
        appliedQueries: res.appliedQueries,
      });
    } catch (error) {
      console.error('Search error:', error);
    }
    
    setLoading(false);
  };

  const handleQuerySearch = useCallback(async (queries) => {
    // if cache is missing, fetch dynamic query results here
    if (!queries || !Array.isArray(queries) || queries.length === 0) return;
    setLoading(true);
    const resultsArr = [];

    for (let i = 0; i < queries.length; i++) {
      const q = queries[i];
      const params = {
        isRefined: true,
        refinedQuery: {
          combined_query: q.combined_query || q.query || "",
        },
        // include any explicit fields if present
        ...(q.cond ? { cond: q.cond } : {}),
        ...(q.intr ? { intr: q.intr } : {}),
        ...(q.other_term ? { other_term: q.other_term } : {}),
      };

      try {
        const res = await searchClinicalTrials(params);
        resultsArr[i] = {
          search_key: res.search_key,
          results: Array.isArray(res.results) ? res.results : [],
          counts: res.counts || { total: 0, merged: 0, pm_only: 0, ctg_only: 0 },
          total: res.total || 0,
          totalPages: res.totalPages || 1,
          filter_stats: res.filter_stats,
          refinedQuery: res.refinedQuery,
          appliedQueries: res.appliedQueries,
        };
      } catch (err) {
        console.debug('[QueryList] Error fetching dynamic query', q, err);
        resultsArr[i] = {
          search_key: null,
          results: [],
          counts: { total: 0, merged: 0, pm_only: 0, ctg_only: 0 },
          total: 0,
          totalPages: 1,
          filter_stats: {},
          refinedQuery: { combined_query: q.combined_query || '' },
          appliedQueries: [],
        };
      }
    }

    setQueryResults(resultsArr);

    try {
      const cacheString = sessionStorage.getItem(SESSION_KEY);
      const parsed = cacheString ? JSON.parse(cacheString) : {};
      parsed.dynamicQueryResults = resultsArr;
      // need to fix
      parsed.dynamicSelectedIndex = null;
      parsed.dynamicResultSelected = false;
      sessionStorage.setItem(SESSION_KEY, JSON.stringify(parsed));
      console.debug('[QueryList] Saved dynamic query results to cache');
    } catch (e) {
      console.debug('[QueryList] Failed to save dynamic query results to cache', e);
    }

    setLoading(false);
  }, []);

  useEffect(() => {
    // Restore cached dynamic query results from sessionStorage only
    let restored = false;
    try {
      const cacheString = sessionStorage.getItem(SESSION_KEY);
      if (cacheString) {
        const parsed = JSON.parse(cacheString);
        if (
          parsed &&
          parsed.dynamicQueryResults &&
          Array.isArray(parsed.dynamicQueryResults) &&
          dynamicQueries?.queries &&
          Array.isArray(dynamicQueries.queries) &&
          parsed.dynamicQueryResults.length === dynamicQueries.queries.length
        ) {
          // Only restore when cached results exist and align with current dynamicQueries
          setQueryResults(parsed.dynamicQueryResults);

          // Restore selection state if available
          if (typeof parsed.dynamicSelectedIndex !== 'undefined' && parsed.dynamicSelectedIndex !== null) {
            setSelected(parsed.dynamicSelectedIndex);
            
            console.debug('[QueryList] Restored dynamicSelectedIndex from cache:', parsed.dynamicSelectedIndex);
          }
          if (typeof parsed.dynamicResultSelected !== 'undefined' && parsed.dynamicResultSelected !== null) {
            setResultSelected(parsed.dynamicResultSelected);
            
            console.debug('[QueryList] Restored dynamicResultSelected from cache:', parsed.dynamicResultSelected);
          }

          restored = true;
          
          console.debug('[QueryList] Restored dynamic query results from cache');
        }
      }
    } catch (e) {
      
      console.debug('[QueryList] Error restoring from cache:', e);
    }

    // If nothing restored, fall back to fetching the dynamic results here
    if (!restored && dynamicQueries?.queries) {
      
      console.debug('[QueryList] No cached dynamic results found; fetching now');
      // populate results by calling handleQuerySearch
      handleQuerySearch(dynamicQueries.queries);
    }
  }, [dynamicQueries, handleQuerySearch]);

  return (
    <div className="mt-6 space-y-4 px-4 w-full max-w-7xl mx-auto">
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-4">
        <button
          className="w-full flex justify-between items-center text-left"
          onClick={() => setShowMore(!showMore)}
        >
          <span className="font-medium text-gray-800">
            Advanced Search Builder
          </span>
          <ChevronDown
            className={`w-5 h-5 text-gray-500 transform transition-transform ${
              showMore ? "rotate-180" : "rotate-0"
            }`}
          />
        </button>

        {showMore && (
          <div className="mt-4 space-y-4">
            <div className="flex flex-row rounded-lg border">
            {/* Builder Interface */}
            <div className="w-1/2 rounded-lg p-4">
             

              {/* Current Term Input Row */}
              <div className="space-y-3">
                <div className="flex items-start gap-2">
                  <div className="flex-1">
                    <label className="text-xs text-gray-600 mb-1 block">
                      Search Term
                    </label>
                    <input
                      type="text"
                      value={currentTerm}
                      onChange={(e) => setCurrentTerm(e.target.value)}
                      className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Enter term or select from below..."
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && currentTerm.trim()) {
                          addToQuery(currentTerm);
                        }
                      }}
                    />
                  </div>
                  
                </div>

                {/* Operator Selection (always visible, no plus icons) */}
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    onClick={() => currentTerm.trim() && addToQuery(currentTerm, "AND", false)}
                    disabled={!currentTerm.trim()}
                    className="px-2 bg-gray-100 py-1 border border-dashed rounded-sm text-sm font-semibold disabled:cursor-not-allowed"
                  >
                    AND
                  </button>
                  <button
                    onClick={() => currentTerm.trim() && addToQuery(currentTerm, "OR", false)}
                    disabled={!currentTerm.trim()}
                    className="px-2 bg-gray-100 py-1 border border-dashed rounded-sm text-sm font-semibold disabled:cursor-not-allowed"
                  >
                    OR
                  </button>
                  <button
                    onClick={() => currentTerm.trim() && addToQuery(currentTerm, "NOT", false)}
                    disabled={!currentTerm.trim()}
                    className="px-2 bg-gray-100 py-1 border border-dashed rounded-sm text-sm font-semibold disabled:cursor-not-allowed"
                  >
                    NOT
                  </button>

                  <button
                    onClick={() => currentTerm.trim() && addToQuery(currentTerm, "AND", true)}
                    disabled={!currentTerm.trim() || !queryString.trim()}
                    className="px-2 bg-gray-100 py-1 border border-dashed rounded-sm text-sm font-semibold disabled:cursor-not-allowed"
                  >
                    ( ) AND
                  </button>
                  <button
                    onClick={() => currentTerm.trim() && addToQuery(currentTerm, "OR", true)}
                    disabled={!currentTerm.trim() || !queryString.trim()}
                    className="px-2 bg-gray-100 py-1 border border-dashed rounded-sm text-sm font-semibold disabled:cursor-not-allowed"
                  >
                    ( ) OR
                  </button>
                  <button
                    onClick={() => currentTerm.trim() && addToQuery(currentTerm, "NOT", true)}
                    disabled={!currentTerm.trim() || !queryString.trim()}
                    className="px-2 bg-gray-100 py-1 border border-dashed rounded-sm text-sm font-semibold disabled:cursor-not-allowed"
                  >
                    ( ) NOT
                  </button>
                </div>
              </div>

              <div className="mt-4">
                <div className="flex flex-wrap gap-2">
                  {Object.keys(allTerms).length > 0 ? (
                    Object.entries(allTerms).map(([category, terms]) => (
                      <div key={category} className="">
                        <h3 className="text-xs font-semibold text-gray-600 mb-1">{category.replace("Refined ", "")}</h3>
                        <div className="flex flex-wrap gap-2">
                          {terms.map((term, idx) => (
                            <button
                              key={`${category}-${idx}`}
                              onClick={() => handleTermClick(term)}
                              className={`px-2 py-1 text-sm font-bold transition-colors ${
                                currentTerm === term
                                  ? "bg-purple-700 text-white"
                                  : "bg-purple-100 text-purple-800 hover:bg-purple-200"
                              }`}
                              title={category}
                            >
                              {term}
                            </button>
                          ))}
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-gray-500 italic">No suggestions available</p>
                  )}
                </div>
              </div>
            </div>

            <div className="w-1/2 rounded-lg p-4 ">
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-semibold text-gray-700">
                  Query Box
                </label>
                <button
                  onClick={clearQuery}
                  className="text-xs text-red-600 hover:text-red-700 font-semibold flex items-center gap-1"
                >
                  Clear
                </button>
              </div>
              
              <textarea
                value={queryString}
                onChange={handleQueryEdit}
                className="w-full border border-gray-300 rounded-md px-3 py-2 font-mono text-sm text-gray-800 min-h-[100px] focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Build your query here or type directly..."
              />
              
              <button
                className="mt-1 text-sm  bg-green-600 text-white font-bold rounded-full py-1 px-3 disabled:bg-gray-400 disabled:cursor-not-allowed"
                onClick={handleAdvancedSearch}
                disabled={!queryString.trim()}
              >
                Search
              </button>

              {/* Results Preview */}
            <div className=" bg-gray-50 border border-gray-200 rounded-md mt-4 p-3">
              <h4 className="text-sm font-bold text-gray-700">
                Results Preview
              </h4>
              {loading && (
                <div className="text-sm mt-2 text-gray-500 flex items-center">
                  Loading...
                </div>
              )}
              {results && results.total > 0 && (
                <div className="mt-2">
                  <div className="flex flex-wrap gap-4 text-sm mb-1">
                    {results.counts?.pm_only > 0 && (
                      <div>
                        <span className="font-bold text-blue-700">PubMed: </span>
                        <span className="text-gray-800">{results.counts.pm_only}</span>
                      </div>
                    )}
                    {results.counts?.ctg_only > 0 && (
                      <div>
                        <span className="font-bold text-green-700">CTG: </span>
                        <span className="text-gray-800">{results.counts.ctg_only}</span>
                      </div>
                    )}
                    {results.counts?.merged > 0 && (
                      <div>
                        <span className="font-bold text-gray-600">Merged: </span>
                        <span className="text-gray-800">{results.counts.merged}</span>
                      </div>
                    )}
                    {results.counts?.total > 0 && (
                      <div>
                        <span className="font-bold text-gray-800">Total: </span>
                        <span className="text-gray-800">{results.counts.total}</span>
                      </div>
                    )}
                  </div>

                  <button
                    className="text-gray-600 hover:underline  rounded-md text-sm "
                    onClick={() => {
                      setResultSelected(true);
                      setSelected(null);
                      handleQuerySelect(results);
                    }}
                  >
                    View Full Results
                  </button>
                </div>
              )}
            </div>
            </div>

          </div>

      

            
          </div>
        )}
      </div>

      {/* Dynamic Queries Section */}
      {dynamicQueries?.queries?.length > 0 && (
        <div className="w-full space-y-2">
   
          {dynamicQueries.queries.map((item, index) => (
            <div
              key={index}
              className={`${
                index === selected ? "ring-2 ring-blue-300" : ""
              } rounded-lg shadow-sm flex flex-col bg-white border border-gray-200 p-4 hover:shadow-md transition-shadow`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="bg-purple-100 rounded-full text-purple-800 text-sm font-bold px-3 py-1">
                  {item.name || ""}
                </span>
                {queryResults?.length > 0 && queryResults[index] && (
                  <button
                    className="text-gray-600 text-sm hover:text-blue-600 hover:underline"
                    onClick={() => {
                      // Persist selection state so SearchPage.restore can pick it up
                      try {
                        const cacheString = sessionStorage.getItem(SESSION_KEY);
                        const parsed = cacheString ? JSON.parse(cacheString) : {};
                        parsed.dynamicSelectedIndex = index;
                        parsed.dynamicResultSelected = true;
                        sessionStorage.setItem(SESSION_KEY, JSON.stringify(parsed));
                        
                        console.debug('[QueryList] Persisted dynamic selection to cache:', index);
                      } catch (e) {
                        
                        console.debug('[QueryList] Failed to persist dynamic selection to cache', e);
                      }

                      setResultSelected(true);
                      setSelected(index);
                      handleQuerySelect(queryResults[index]);
                    }}
                  >
                    Total: {queryResults[index].counts?.total} | 
                    PM: {queryResults[index].counts?.pm_only} | 
                    CTG: {queryResults[index].counts?.ctg_only} | 
                    Merged: {queryResults[index].counts?.merged}
                  </button>
                )}
              </div>
              
              <div className="text-sm">
                {item.name && item.name.includes("Condition") && item.cond && (
                  <div className="my-2 flex flex-wrap gap-1">
                    {item.cond.split(' OR ').map((condPart, i, arr) => (
                      <div key={i} className="flex items-center">
                        <span className={`text-xs px-2 py-1 font-semibold  ${
                          i === 0 ? 'bg-gray-100 text-gray-800' : 'bg-blue-100 text-blue-800'
                        }`}>
                          {condPart}
                        </span>
                        {i < arr.length - 1 && (
                          <span className="mx-1 font-bold text-gray-500">+</span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
                {item.name && item.name.includes("Intervention") && item.intr && (
                  <div className="my-2 flex flex-wrap gap-1">
                    {item.intr.split(' OR ').map((intrPart, i, arr) => (
                      <div key={i} className="flex items-center">
                        <span className={`text-xs px-2 py-1 font-semibold  ${
                          i === 0 ? 'bg-gray-100 text-gray-800' : 'bg-blue-100 text-blue-800'
                        }`}>
                          {intrPart}
                        </span>
                        {i < arr.length - 1 && (
                          <span className="mx-1 font-bold text-gray-500">+</span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
                {item.name && item.name.includes("Other") && item.other_term && (
                  <div className="my-2 flex flex-wrap gap-1">
                    {item.other_term.split(' OR ').map((other, i, arr) => (
                      <div key={i} className="flex items-center">
                        <span className={`text-xs px-2 py-1 font-semibold  ${
                          i === 0 ? 'bg-gray-100 text-gray-800' : 'bg-blue-100 text-blue-800'
                        }`}>
                          {other}
                        </span>
                        {i < arr.length - 1 && (
                          <span className="mx-1 font-bold text-gray-500">+</span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
                <div className="mt-2 p-2 bg-gray-50 rounded font-mono text-xs text-gray-700">
                  {item.combined_query}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {resultSelected && (
        <button
          className="hover:underline p-2 text-sm text-gray-600 font-semibold"
          onClick={() => {
            // Clear selection state locally AND from cache
            setSelected(null);
            setResultSelected(false);

            // Clear dynamic selection from cache so it doesn't restore on next page load
            try {
              const cacheString = sessionStorage.getItem(SESSION_KEY);
              const parsed = cacheString ? JSON.parse(cacheString) : {};
              parsed.dynamicSelectedIndex = null;
              parsed.dynamicResultSelected = false;
              sessionStorage.setItem(SESSION_KEY, JSON.stringify(parsed));
              console.debug('[QueryList] Cleared dynamicSelectedIndex/dynamicResultSelected from cache');
            } catch (e) {
              console.debug('[QueryList] Failed to clear dynamic selection from cache', e);
            }

            // If `baseResults` prop is empty (timing/restore issue), try to read from session cache
            if (!baseResults || Object.keys(baseResults).length === 0) {
              try {
                const cacheString = sessionStorage.getItem(SESSION_KEY);
                const parsed = cacheString ? JSON.parse(cacheString) : {};
                const fallback = parsed.baseResults || (parsed.pageCache && parsed.pageCache[parsed.currentPage] && parsed.pageCache[parsed.currentPage].results) || {};
                
                console.debug('[QueryList] baseResults prop empty — using fallback from cache:', fallback);
                handleQuerySelect(fallback);
                return;
              } catch (e) {
                
                console.debug('[QueryList] Failed to read baseResults from cache fallback', e);
              }
            }

            handleQuerySelect(baseResults);
          }}
        >
          ← View Original Search Results
        </button>
      )}
    </div>
  );
};

QueryList.propTypes = {
  dynamicQueries: PropTypes.object.isRequired,
  handleQuerySelect: PropTypes.func.isRequired,
  baseResults: PropTypes.object.isRequired,
};

export default QueryList;
