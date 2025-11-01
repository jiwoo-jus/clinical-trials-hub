import { ChevronsDownUp, ChevronsUpDown, Loader2 } from 'lucide-react';
import PropTypes from 'prop-types';
import React, { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react';

// Added useEffect

import FullText from './FullText';

const BASE_URL = (() => {
  if (process.env.NODE_ENV === 'development') {
    return process.env.REACT_APP_API_URL || 'http://localhost:5050';
  }
  return process.env.REACT_APP_API_URL || 'https://cth-backend-103266204202.us-central1.run.app';
})();

console.log('ReferenceList BASE_URL:', BASE_URL);

// Remove the old single getPmcidFromPmid helper function
// async function getPmcidFromPmid(pmid) { ... } // REMOVED

// Accept onActiveReferenceChange in props
const ReferenceList = forwardRef(({ references, onActiveReferenceChange }, ref) => {
  const [expandedReferenceIndex, setExpandedReferenceIndex] = useState(null);
  const [referenceFullText, setReferenceFullText] = useState('');
  const [isFetchingReference, setIsFetchingReference] = useState(false);
  const referenceFullTextRef = useRef(null);
  const [pmcidMap, setPmcidMap] = useState({}); // State to store PMID -> PMCID mapping
  const [loadingPmcids, setLoadingPmcids] = useState(false); // State for loading indicator

  // Fetch PMCIDs in batch when references change
  useEffect(() => {
    // ... (useEffect logic remains the same) ...
    const pmidsInReferences = references
      ?.map(ref => ref.pmid)
      .filter(pmid => pmid); // Get all valid PMIDs from references

    // Filter out PMIDs that are already present in pmcidMap (regardless of value)
    const pmidsToFetchArray = pmidsInReferences?.filter(pmid => !(pmid in pmcidMap)) || [];

    if (pmidsToFetchArray.length > 0) {
      const pmidsToFetchString = pmidsToFetchArray.join(',');
      setLoadingPmcids(true);

      fetch(`${BASE_URL}/api/utils/pmid_to_pmcid_batch?pmids=${pmidsToFetchString}`)
        .then(res => {
          if (!res.ok) {
            throw new Error(`HTTP error! status: ${res.status}`);
          }
          return res.json();
        })
        .then(records => {
          const mapUpdate = {};
          // Create a quick lookup map from the response records
          const responseMap = records.reduce((acc, record) => {
            if (record.pmid) {
              // Store the PMCID if available, otherwise mark as attempted (null)
              acc[record.pmid] = record.pmcid || null;
            }
            return acc;
          }, {});

          // For every PMID we requested, add an entry to mapUpdate
          pmidsToFetchArray.forEach(pmid => {
            // Use the found PMCID from responseMap, or null if not found/error
            mapUpdate[pmid] = responseMap[pmid] !== undefined ? responseMap[pmid] : null;
          });

          // Merge new results with existing map
          setPmcidMap(prevMap => ({ ...prevMap, ...mapUpdate }));
          console.log("Fetched PMCID map update:", mapUpdate);
        })
        .catch(error => {
          console.error("Error fetching PMCID batch:", error);
          // On error, mark all requested PMIDs as attempted (null) to prevent retries
          const errorMapUpdate = {};
          pmidsToFetchArray.forEach(pmid => {
            errorMapUpdate[pmid] = null; // Mark as attempted even on fetch error
          });
          setPmcidMap(prevMap => ({ ...prevMap, ...errorMapUpdate }));
        })
        .finally(() => {
          setLoadingPmcids(false);
        });
    }
  }, [references, pmcidMap]); // Add pmcidMap to the dependency array

  // Expose the highlightEvidence function via ref
  useImperativeHandle(ref, () => ({
    highlightEvidence: (evidenceText) => {
      referenceFullTextRef.current?.highlightEvidence?.(evidenceText);
    },
    // Highlight within the currently selected/expanded reference's FullText
    highlightEvidenceInSelected: (evidenceText) => {
        if (expandedReferenceIndex !== null && referenceFullTextRef.current) {
            referenceFullTextRef.current.highlightEvidence(evidenceText);
            return true; // Indicate highlighting was attempted
        }
        console.warn("HighlightEvidenceInSelected called but no reference is expanded.");
        return false; // Indicate no expanded reference to highlight in
    }
  }));

  const handleReferenceToggle = async (index, refData) => {
    // ... (handleReferenceToggle logic remains the same) ...
    if (index === expandedReferenceIndex) {
      setExpandedReferenceIndex(null);
      setReferenceFullText('');
      // Call callback with null when collapsing
      if (onActiveReferenceChange) {
          onActiveReferenceChange(null);
      }
    } else {
      setIsFetchingReference(true);
      setExpandedReferenceIndex(index);
      setReferenceFullText(''); // Clear previous text
      // We will call onActiveReferenceChange after fetch attempt

      try {
        // Use PMCID directly from refData if available, otherwise check the fetched map
        let targetPmcid = refData.pmcid || pmcidMap[refData.pmid];

        // If still no PMCID after checking map, maybe log or handle?
        // (The old single fetch is removed, relying on the batch fetch now)
        if (!targetPmcid) {
           console.warn(`No PMCID found for PMID ${refData.pmid} in refData or fetched map.`);
           // Optionally, try a single fetch as a fallback? Or just show message.
           // For now, show message:
           setReferenceFullText('<p>Full text not available (No PMCID found).</p>');
           setIsFetchingReference(false);
           // Call callback with null as we couldn't get the info
           if (onActiveReferenceChange) {
               onActiveReferenceChange(null);
           }
           return;
        }

        // Fetch full text using the determined PMCID
        const res = await fetch(`${BASE_URL}/api/paper/pmc_full_text_html?pmcid=${targetPmcid}`);
        if (!res.ok) throw new Error(`HTTP error fetching full text! status: ${res.status}`);
        const htmlString = await res.text();

        // Declare a variable to hold the processed full text
        let processedFullText = '';

        // Parse and clean HTML
        const parser = new DOMParser();
        const doc = parser.parseFromString(htmlString, 'text/html');
        const article = doc.querySelector("#main-content > article");
        if (article) {
          article.querySelectorAll("ul.d-buttons.inline-list").forEach(el => el.remove());
          article.querySelectorAll("section").forEach(section => {
            if (section.getAttribute("aria-label") === "Article citation and metadata") {
              section.remove();
            }
          });
          // Assign the cleaned HTML to the variable
          processedFullText = article.outerHTML;
        } else {
          // Assign the raw HTML string (or fallback) to the variable
          processedFullText = htmlString || '<p>Full text content not found in response.</p>';
        }

        // Set the state using the processed text
        setReferenceFullText(processedFullText);

        // Call callback with the processed text
        if (onActiveReferenceChange) {
            onActiveReferenceChange({ pmcid: targetPmcid, fullText: processedFullText });
        }

      } catch (error) {
        console.error("Error fetching reference full text:", error);
        setReferenceFullText('<p>Error loading reference full text.</p>');
        // Call callback with null on error
        if (onActiveReferenceChange) {
            onActiveReferenceChange(null);
        }
      } finally {
        setIsFetchingReference(false);
      }
    }
  };

  // Grouping logic (remains the same)
  const groupMap = {
    BACKGROUND: 'General',
    RESULT: 'Study Results',
    DERIVED: 'From PubMed',
  };
  const groupDescriptions = {
    General: 'These publications are provided voluntarily by the person who enters information about the study.',
    'Study Results': 'These publications are about the study results.',
    'From PubMed': 'These publications come from PubMed, a public database of scientific and medical articles.',
    Other: 'Other related publications.',
  };

  const groups = {};
  references.forEach((ref) => {
    const groupName = groupMap[ref.type] || 'Other';
    if (!groups[groupName]) {
      groups[groupName] = [];
    }
    groups[groupName].push(ref);
  });

  return (
    <>
      <h2 className="text-xl font-semibold text-custom-blue-deep border-b border-custom-border pb-2 mb-4">
        References
      </h2>
      {references.length > 0 ? (
        <>
          {Object.entries(groups).map(([groupName, refs]) => (
            <div key={groupName} className="mb-6">
              <h3 className="font-semibold text-base mb-1">{groupName}</h3>
              {groupDescriptions[groupName] && (
                <p className="text-sm text-custom-text-subtle mb-3">{groupDescriptions[groupName]}</p>
              )}
              <div className="space-y-4 text-sm">
                {/* Remove the unused 'index' parameter */}
                {refs.map((ref) => {
                  // Use findIndex on the original references array to get the global index
                  const originalIndex = references.findIndex(r =>
                    r.pmid === ref.pmid && r.citation === ref.citation);
                  const displayPmcid = ref.pmcid || pmcidMap[ref.pmid]; // Get PMCID from ref or map
                  const isExpanded = originalIndex === expandedReferenceIndex; // Check if this item is expanded

                  return (
                    // Add conditional styling for highlighting the expanded item
                    <div
                      key={ref.pmid || `${groupName}-${originalIndex}`} // Use originalIndex for key consistency
                      className={`border-b border-custom-border-light pb-3 last:border-b-0 p-3 rounded-md transition-colors duration-200 ${
                        isExpanded ? 'bg-custom-blue-lightest border-l-4 border-l-custom-blue' : 'bg-white' // Highlight style
                      }`}
                    >
                      <div className="mb-1 flex items-start gap-2"> {/* Use flex for numbering */}
                        {/* Add numbering */}
                        <span className="font-semibold text-custom-text-subtle w-5 text-right">
                          {originalIndex + 1}.
                        </span>
                        <span className="flex-1"> {/* Citation takes remaining space */}
                          {ref.citation || 'No citation available'}
                        </span>
                      </div>
                      {/* Display PMID and PMCID links */}
                      {(ref.pmid || displayPmcid) && (
                        <div className="text-xs text-custom-text-subtle mb-2 ml-7"> {/* Indent links to align with citation */}
                          {ref.pmid && (
                            <a
                              href={`https://pubmed.ncbi.nlm.nih.gov/${ref.pmid}/`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-custom-blue hover:underline"
                            >
                              PMID: {ref.pmid}
                            </a>
                          )}
                          {/* Show separator only if both exist */}
                          {ref.pmid && displayPmcid && <span className="mx-1">|</span>}
                          {displayPmcid && (
                            <a
                              href={`https://www.ncbi.nlm.nih.gov/pmc/articles/${displayPmcid}/`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-custom-blue hover:underline"
                            >
                              PMCID: {displayPmcid}
                            </a>
                          )}
                          {/* Optional: Show loading indicator per item if needed */}
                          {ref.pmid && !displayPmcid && loadingPmcids && <span className="ml-2 text-xs">(loading PMCID...)</span>}
                        </div>
                      )}
                      {/* Expand button - enable only if displayPmcid exists */}
                      <div className="ml-7"> {/* Indent button */}
                        <button
                          onClick={() => handleReferenceToggle(originalIndex, ref)}
                          // Disable if fetching this specific item OR if displayPmcid is falsy (null, undefined, '')
                          disabled={(isFetchingReference && isExpanded) || !displayPmcid}
                          className={`flex items-center gap-1 text-xs px-2 py-0.5 rounded ${
                            isExpanded
                              ? 'bg-custom-blue-light text-custom-blue-deep' // Slightly darker bg when expanded
                              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                          } transition-colors disabled:opacity-50 disabled:cursor-not-allowed`} // Add disabled cursor style
                          title={!displayPmcid ? "Full text requires PMCID" : (isExpanded ? 'Collapse Full Text' : 'Expand Full Text')} // Add tooltip for disabled state
                        >
                          {isFetchingReference && isExpanded ? (
                            <Loader2 size={12} className="animate-spin" />
                          ) : isExpanded ? (
                            <ChevronsDownUp size={12} />
                          ) : (
                            <ChevronsUpDown size={12} />
                          )}
                          {isExpanded ? 'Collapse Full Text' : 'Expand Full Text'}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </>
      ) : (
        <p className="text-custom-text-subtle">No references available.</p>
      )}
      {/* Full text display area */}
      {expandedReferenceIndex !== null && (
        <div className="mt-4 pt-4 border-t border-custom-border">
          {/* Use originalIndex + 1 for the title */}
          <h3 className="text-lg font-semibold text-custom-blue-deep mb-2">
            Full Text for Reference {expandedReferenceIndex + 1}
          </h3>
          {isFetchingReference ? (
             <div className="flex justify-center items-center h-20">
               <Loader2 size={24} className="animate-spin text-custom-blue-deep" />
             </div>
          ) : (
             <FullText ref={referenceFullTextRef} fullText={referenceFullText} />
          )}
        </div>
      )}
    </>
  );
});

// Add the displayName property here
ReferenceList.displayName = 'ReferenceList';

// Define propTypes
ReferenceList.propTypes = {
  references: PropTypes.arrayOf(PropTypes.shape({
    type: PropTypes.string,
    pmid: PropTypes.string,
    pmcid: PropTypes.string, // Keep this, might be provided directly
    citation: PropTypes.string,
  })).isRequired,
  onActiveReferenceChange: PropTypes.func, // Add prop type for the callback
};

export default ReferenceList;