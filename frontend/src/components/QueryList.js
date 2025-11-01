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

  // Tree-based query structure for each term type
  const [queryTrees, setQueryTrees] = useState({
    Condition: [],
    Intervention: [],
    Other: [],
  });

  // Track available terms and adding state
  const [addingTerm, setAddingTerm] = useState({
    Condition: false,
    Intervention: false,
    Other: false,
  });

  const [newTermText, setNewTermText] = useState({
    Condition: "",
    Intervention: "",
    Other: "",
  });

  const getTermType = (type) => {
    if (type.includes("Condition")) return "Condition";
    if (type.includes("Intervention")) return "Intervention";
    return "Other";
  };

  // Build query string from tree structure
  const buildQueryFromTree = useCallback((tree) => {
    if (!tree || tree.length === 0) return "";

    const buildNode = (node) => {
      if (node.type === 'term') {
        return node.value;
      } else if (node.type === 'group') {
        const childQueries = node.children.map(buildNode);
        return `(${childQueries.join(` ${node.operator} `)})`;
      }
      return "";
    };

    if (tree.length === 1) {
      return buildNode(tree[0]);
    }

    // Join root level nodes with their operators
    const parts = tree.map((node, index) => {
      const nodeStr = buildNode(node);
      if (index < tree.length - 1) {
        return `${nodeStr} ${node.nextOperator || 'OR'}`;
      }
      return nodeStr;
    });

    return parts.join(' ');
  }, []);

  // Check if a term already exists in the tree
  const termExistsInTree = (tree, termValue) => {
    const checkNode = (node) => {
      if (node.type === 'term') {
        return node.value === termValue;
      } else if (node.type === 'group') {
        return node.children.some(checkNode);
      }
      return false;
    };
    return tree.some(checkNode);
  };

  // Add term to query tree
  const addTermToTree = (termType, termValue, mode) => {
    setQueryTrees((prev) => {
      const currentTree = [...prev[termType]];

      // Check for duplicates
      if (termExistsInTree(currentTree, termValue)) {
        return prev;
      }

      const newNode = { type: 'term', value: termValue };

      // If tree is empty, just add the term
      if (currentTree.length === 0) {
        return { ...prev, [termType]: [newNode] };
      }

      // Handle different modes
      if (mode === 'add-AND' || mode === 'add-OR') {
        const operator = mode === 'add-AND' ? 'AND' : 'OR';
        // Set the operator on the last node
        currentTree[currentTree.length - 1].nextOperator = operator;
        currentTree.push(newNode);
        return { ...prev, [termType]: currentTree };
      }

      if (mode === 'nest-AND' || mode === 'nest-OR') {
        if (currentTree.length < 2) {
          // Fallback to add if not enough terms
          currentTree[currentTree.length - 1].nextOperator = mode === 'nest-AND' ? 'AND' : 'OR';
          currentTree.push(newNode);
          return { ...prev, [termType]: currentTree };
        }

        const operator = mode === 'nest-AND' ? 'AND' : 'OR';
        // Take the last node and create a group with it
        const lastNode = currentTree.pop();
        const groupNode = {
          type: 'group',
          operator: operator,
          children: [lastNode, newNode]
        };

        // Preserve the operator that was on the last node
        if (lastNode.nextOperator) {
          groupNode.nextOperator = lastNode.nextOperator;
          delete lastNode.nextOperator;
        }

        currentTree.push(groupNode);
        return { ...prev, [termType]: currentTree };
      }

      return prev;
    });
  };

  // Remove term from tree
  const removeTermFromTree = (termType, termValue) => {
    setQueryTrees((prev) => {
      const removeFromNode = (nodes) => {
        const result = [];
        for (let i = 0; i < nodes.length; i++) {
          const node = nodes[i];
          
          if (node.type === 'term') {
            if (node.value !== termValue) {
              result.push(node);
            } else {
              // If we're removing this term and it has a nextOperator, 
              // we need to handle operator cleanup
              if (i > 0 && node.nextOperator) {
                // Remove the operator from previous node
                delete result[result.length - 1].nextOperator;
              }
            }
          } else if (node.type === 'group') {
            const newChildren = removeFromNode(node.children);
            if (newChildren.length > 1) {
              result.push({ ...node, children: newChildren });
            } else if (newChildren.length === 1) {
              // Unwrap single-child groups
              const unwrapped = newChildren[0];
              if (node.nextOperator) {
                unwrapped.nextOperator = node.nextOperator;
              }
              result.push(unwrapped);
            }
            // If newChildren.length === 0, don't add anything
          }
        }
        return result;
      };

      return { ...prev, [termType]: removeFromNode(prev[termType]) };
    });
  };

  // Check if term is in tree
  const isTermInTree = (termType, termValue) => {
    return termExistsInTree(queryTrees[termType], termValue);
  };

  // Handle custom term addition
  const handleAddCustomTerm = (type) => {
    const term = newTermText[type].trim();
    if (!term) return;

    // Add as a simple term with OR (default)
    if (queryTrees[type].length > 0) {
      addTermToTree(type, term, 'add-OR');
    } else {
      setQueryTrees((prev) => ({
        ...prev,
        [type]: [{ type: 'term', value: term }]
      }));
    }

    setNewTermText((prev) => ({ ...prev, [type]: "" }));
    setAddingTerm((prev) => ({ ...prev, [type]: false }));
  };

  // Build combined query
  const buildCombinedQuery = useCallback(() => {
    const cond = buildQueryFromTree(queryTrees.Condition);
    const intr = buildQueryFromTree(queryTrees.Intervention);
    const other = buildQueryFromTree(queryTrees.Other);
    
    const queryParts = [];
    if (cond) queryParts.push(`(${cond})`);
    if (intr) queryParts.push(`(${intr})`);
    if (other) queryParts.push(`(${other})`);
    
    return queryParts.join(" AND ");
  }, [queryTrees, buildQueryFromTree]);

  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    setSearchTerm(buildCombinedQuery());
  }, [buildCombinedQuery]);

  // Handle advanced search
  const handleAdvancedSearch = async () => {
    setLoading(true);
    setResults({});
    
    const params = {
      cond: buildQueryFromTree(queryTrees.Condition),
      intr: buildQueryFromTree(queryTrees.Intervention),
      other_term: buildQueryFromTree(queryTrees.Other),
      isRefined: true,
      refinedQuery: {
        cond: buildQueryFromTree(queryTrees.Condition),
        intr: buildQueryFromTree(queryTrees.Intervention),
        other_term: buildQueryFromTree(queryTrees.Other),
        combined_query: searchTerm,
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
          <>
            <div className="text-sm mt-3 flex items-center w-full">
              <div className="w-full border rounded-md bg-gray-50 px-3 py-2">
                <span
                  className={`${
                    searchTerm ? "font-mono text-gray-800 text-sm" : "text-gray-600"
                  }`}
                >
                  {searchTerm || "Select terms to build query"}
                </span>
              </div>
              <button
                className="ml-3 bg-green-600 hover:bg-green-700 text-white font-bold rounded-lg py-2 px-4 whitespace-nowrap"
                onClick={handleAdvancedSearch}
                disabled={!searchTerm}
              >
                SEARCH
              </button>
            </div>

            <div className="mt-4">
              {dynamicQueries?.queries?.map((q, index) => {
                const type = getTermType(q.name);
                const localQuery = buildQueryFromTree(queryTrees[type]);

                return (
                  <div key={index} className="text-sm mt-4 border border-gray-200 rounded-lg px-3 pb-3 pt-2 bg-gray-50">
                    {/* Section Title */}
                    <div className="flex justify-between items-center mb-1 ml-0.5">
                      <span className="font-bold text-gray-800 text-base">{type} Terms</span>
                      <button
                        className="text-red-600 text-xs font-semibold rounded px-2 hover:underline"
                        onClick={() => {
                          setQueryTrees((prev) => ({ ...prev, [type]: [] }));
                        }}
                      >
                        Clear All
                      </button>
                    </div>

                    {/* Local Query Preview */}
                    <div className="w-full border border-gray-300 bg-white rounded-md px-3 py-2 text-sm font-mono text-gray-800 mb-3  flex items-center">
                      {localQuery || <span className="text-gray-500 font-sans">No terms selected</span>}
                    </div>

                    {/* Available Terms */}
                    <div className="">
                      <div className="flex flex-wrap gap-2">
                        {q.terms.map((term, idx) => {
                          const inTree = isTermInTree(type, term);
                          const canNest = queryTrees[type].length >= 1;

                          return (
                            <div key={idx} className="flex items-center gap-1">
                              <button
                                className={`px-2 py-1 font-semibold text-xs transition-colors ${
                                  inTree
                                    ? "bg-purple-700 text-white"
                                    : "bg-purple-100 text-purple-700 hover:bg-purple-200"
                                }`}
                                onClick={() => {
                                  if (inTree) {
                                    removeTermFromTree(type, term);
                                  } else {
                                    // Default add with OR if tree is not empty
                                    if (queryTrees[type].length > 0) {
                                      addTermToTree(type, term, 'add-OR');
                                    } else {
                                      setQueryTrees((prev) => ({
                                        ...prev,
                                        [type]: [{ type: 'term', value: term }]
                                      }));
                                    }
                                  }
                                }}
                              >
                                {term}
                                
                              </button>

                              {!inTree && queryTrees[type].length > 0 && (
                                <select
                                  className="text-xs border border-gray-300 px-2 py-1 bg-white text-gray-700"
                                  onChange={(e) => {
                                    const val = e.target.value;
                                    if (val === "NONE") return;
                                    addTermToTree(type, term, val);
                                    e.target.value = "NONE";
                                  }}
                                  defaultValue="NONE"
                                >
                                  <option value="NONE">Add with...</option>
                                  <option value="add-AND">AND</option>
                                  <option value="add-OR">OR</option>
                                  {canNest && <option value="nest-AND">Nest with AND</option>}
                                  {canNest && <option value="nest-OR">Nest with OR</option>}
                                </select>
                              )}
                            </div>
                          );
                        })}

                        {/* Add Custom Term */}
                        {addingTerm[type] ? (
                          <div className="flex items-center gap-2">
                            <input
                              type="text"
                              className="border border-gray-300 px-2 py-1 text-sm rounded-md"
                              value={newTermText[type]}
                              onChange={(e) =>
                                setNewTermText((prev) => ({ ...prev, [type]: e.target.value }))
                              }
                              placeholder="Enter custom term"
                              onKeyDown={(e) => {
                                if (e.key === "Enter") handleAddCustomTerm(type);
                                if (e.key === "Escape") setAddingTerm((prev) => ({ ...prev, [type]: false }));
                              }}
                              autoFocus
                            />
                            <button
                              className="bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded-md text-xs font-semibold"
                              onClick={() => handleAddCustomTerm(type)}
                            >
                              Add
                            </button>
                            <button
                              className="text-gray-500 hover:text-gray-700 text-xs"
                              onClick={() => setAddingTerm((prev) => ({ ...prev, [type]: false }))}
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <button
                            className="px-2 py-1 flex items-center justify-center rounded-full bg-white border-2 border-dashed border-gray-300 hover:border-gray-400 text-gray-600 hover:bg-gray-50"
                            onClick={() => setAddingTerm((prev) => ({ ...prev, [type]: true }))}
                            title="Add custom term"
                          >
                            <Plus className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </div>

                  </div>
                );
              })}
            </div>

            {/* Results Preview */}
            <div className="mt-4 w-1/2 border rounded-lg px-4 py-3 bg-white">
              <span className="text-sm font-bold text-gray-700">
                Results Preview
              </span>
              {loading && (
                <div className="text-sm  text-gray-500 flex items-center">
                  <div className="rounded-full h-4 w-4 border-b-2 border-gray-900 mr-2"></div>
                  Loading...
                </div>
              )}
              {results && results.total > 0 && (
                <div className="mt-1">
                  <div className="flex flex-wrap gap-4 text-sm">
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
                    className="mt-1 hover:underline text-blue-800 rounded-md text-sm font-semibold"
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
              {!loading && (!results || results.total === 0) && searchTerm && (
                <div className="text-sm mt-3 text-gray-500">
                  Click SEARCH to see results
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {/* Dynamic Queries Section */}
      {dynamicQueries?.queries?.length > 0 && (
        <div className="w-full space-y-2">
         
          {dynamicQueries.queries.map((item, index) => (
            <div
              key={index}
              className={`${
                index === selected ? "ring-2 ring-gray-200" : ""
              } rounded-lg shadow-sm flex flex-col bg-white border border-gray-200 p-4 hover:shadow-md transition-shadow`}
            >
              <div className="flex items-center justify-between mb-1">
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
                        <span className={`text-xs px-2 py-1 font-semibold ${
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
                        <span className={`text-xs px-2 py-1 font-semibold ${
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
