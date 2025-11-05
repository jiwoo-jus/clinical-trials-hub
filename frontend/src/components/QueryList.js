import React, { useState, useCallback, useEffect } from 'react';
import PropTypes from 'prop-types';
import { searchClinicalTrials } from '../api/searchApi';
import { ChevronDown, Plus } from 'lucide-react';

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
  const [operator, setOperator] = useState("AND");

  // Collect all terms from dynamic queries
  const allTerms = dynamicQueries?.queries?.flatMap(q => 
    q.terms?.map(term => ({
      value: term,
      category: q.name
    })) || []
  ) || [];

  // Add term to query string
  const addToQuery = (term, op = operator, nest = false) => {
    let newQuery = queryString.trim();
    
    // Format term with field if not "All Fields"
    let formattedTerm = term;


    if (newQuery === "") {
      // First term - just add it
      newQuery = formattedTerm;
    } else if (nest) {
      // Nesting: wrap the existing query with the new term
      if (op === "NOT") {
        newQuery = `(${newQuery}) NOT ${formattedTerm}`;
      } else {
        newQuery = `(${newQuery} ${op} ${formattedTerm})`;
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

  // Handle query search for dynamic queries
  const handleQuerySearch = useCallback(async (dynamicq) => {
    let dynamicResults = [];
    if (dynamicq) {
      for (const item of dynamicq) {
        const params = {
          cond: item.cond || "",
          intr: item.intr || "",
          other_term: item.other_term || "",
          isRefined: true,
          refinedQuery: {
            cond: item.cond || "",
            intr: item.intr || "",
            other_term: item.other_term || "",
            combined_query: item.combined_query || "",
          },
        };
        const res = await searchClinicalTrials(params);
        dynamicResults.push({
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
      }
    }
    setQueryResults(dynamicResults);
  }, []);

  useEffect(() => {
    if (dynamicQueries?.queries) {
      setTimeout(() => {
        handleQuerySearch(dynamicQueries.queries);
      }, 100);
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

                {/* Operator Selection and Add Button */}
                <div className="flex items-center gap-2">
                  <select
                    value={operator}
                    onChange={(e) => setOperator(e.target.value)}
                    className="border border-gray-300 rounded-md px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="AND">AND</option>
                    <option value="OR">OR</option>
                    <option value="NOT">NOT</option>
                  </select>

                  <button
                    onClick={() => currentTerm.trim() && addToQuery(currentTerm, operator, false)}
                    disabled={!currentTerm.trim()}
                    className="px-2 py-1 rounded-full border  text-black text-sm font-semibold disabled:cursor-not-allowed flex items-center gap-1"
                  >
                    <Plus className="w-4 h-4" />
                  </button>

                  <button
                    onClick={() => currentTerm.trim() && addToQuery(currentTerm, "AND", true)}
                    disabled={!currentTerm.trim() || !queryString.trim()}
                    className="px-2 py-1  bg-blue-600 text-white text-sm font-semibold  disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-1"
                  >
                    Add with AND
                  </button>

                  <button
                    onClick={() => currentTerm.trim() && addToQuery(currentTerm, "OR", true)}
                    disabled={!currentTerm.trim() || !queryString.trim()}
                    className="px-2 py-1  bg-blue-600 text-white text-sm font-semibold  disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-1"
                  >
                    Add with OR
                  </button>

                  <button
                    onClick={() => currentTerm.trim() && addToQuery(currentTerm, "NOT", true)}
                    disabled={!currentTerm.trim() || !queryString.trim()}
                    className="px-2 py-1  bg-blue-600 text-white text-sm font-semibold  disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-1"
                  >
                    Add with NOT
                  </button>
                </div>
              </div>

              <div className="mt-4">
                <h4 className="text-xs font-semibold text-gray-600 mb-2">
                  Terms
                </h4>
                <div className="flex flex-wrap gap-2">
                  {allTerms.length > 0 ? (
                    allTerms.map((item, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleTermClick(item.value)}
                        className={`px-2 py-1 text-sm font-bold transition-colors ${
                          currentTerm === item.value
                            ? "bg-purple-700 text-white "
                            :  "bg-purple-100 text-purple-800 hover:bg-purple-200"
                        }`}
                        title={item.category}
                      >
                        {item.value}
                      </button>
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
                className="mt-1 text-sm  bg-green-600 hover:bg-blue-700 text-white font-bold rounded-full py-1 px-3 disabled:bg-gray-400 disabled:cursor-not-allowed"
                onClick={handleAdvancedSearch}
                disabled={!queryString.trim()}
              >
                Search
              </button>
            </div>

          </div>

      

            {/* Results Preview */}
            <div className="border border-gray-200 rounded-lg p-4 bg-white">
              <h4 className="text-sm font-bold text-gray-700 mb-2">
                Results Preview
              </h4>
              {loading && (
                <div className="text-sm text-gray-500 flex items-center">
                  <div className="rounded-full h-4 w-4 border-b-2 border-gray-900 mr-2"></div>
                  Loading...
                </div>
              )}
              {results && results.total > 0 && (
                <div>
                  <div className="flex flex-wrap gap-4 text-sm mb-3">
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
                        <span className="text-gray-900 font-semibold">{results.counts.total}</span>
                      </div>
                    )}
                  </div>

                  <button
                    className="text-blue-600 hover:underline  rounded-md text-sm font-semibold"
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
              {!loading && (!results || results.total === 0) && queryString && (
                <div className="text-sm text-gray-500">
                  Click Search to see results
                </div>
              )}
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
                index === selected ? "ring-2 ring-blue-400" : ""
              } rounded-lg shadow-sm flex flex-col bg-white border border-gray-200 p-4 hover:shadow-md transition-shadow`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="bg-purple-100 rounded-full text-purple-700 text-sm font-bold px-3 py-1">
                  {item.name || ""}
                </span>
                {queryResults?.length > 0 && queryResults[index] && (
                  <button
                    className="text-gray-600 text-sm hover:text-blue-600 hover:underline"
                    onClick={() => {
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
                        <span className={`text-xs px-2 py-1 font-semibold rounded ${
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
                        <span className={`text-xs px-2 py-1 font-semibold rounded ${
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
                        <span className={`text-xs px-2 py-1 font-semibold rounded ${
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
          className="hover:underline p-2 text-sm text-blue-600 font-semibold"
          onClick={() => {
            setSelected(null);
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
