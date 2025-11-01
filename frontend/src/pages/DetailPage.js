import React, { useCallback, useEffect, useRef, useState, useMemo } from 'react';
import queryString from 'query-string';
import { useLocation, useNavigate } from 'react-router-dom';
import { getStructuredInfo, getCtgDetail, getPmcFullTextHtml } from '../api/paperApi';
import ChatBot from '../components/ChatBot';
import FullText from '../components/FullText';
import ReferenceList from '../components/ReferenceList';
import StructuredInfoTabs from '../components/StructuredInfoTabs';
import MeSHGlossary from '../components/MeSHGlossary';
import Header from '../components/Header';
import { ChevronsDownUp, ChevronsUpDown, ArrowUp } from 'lucide-react';

// const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5050';

const DetailPage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { paperId, pmcid, nctId, source } = queryString.parse(location.search);
  const metadata = useMemo(() => location.state?.metadata || {}, [location.state?.metadata]);

  const currentPmcid = pmcid || metadata.pmcid || '';

  const [structuredInfo, setStructuredInfo] = useState(
    metadata.structured_info || null
  );
  const [fullText, setFullText] = useState(''); // Set initial state to empty string
  const [fullTextExpanded, setFullTextExpanded] = useState(false);
  const [selectedReferenceInfo, setSelectedReferenceInfo] = useState(null);
  const [isDataLoaded, setIsDataLoaded] = useState(false);

  const fullTextRef = useRef(null);
  const referenceListRef = useRef(null);
  const loadedKeysRef = useRef(new Set()); // Track loaded keys to prevent duplicate API calls

  useEffect(() => {
    let isMounted = true;
    // reset on id/source change
    setSelectedReferenceInfo(null);

    // Create a unique key for this request
    const requestKey = `${source}-${currentPmcid || nctId}`;
    
    // Skip if we already loaded this request or have structured_info from metadata
    if (loadedKeysRef.current.has(requestKey) || (metadata.structured_info && source !== 'PMC' && source !== 'PM')) {
      if (metadata.structured_info && !structuredInfo) {
        setStructuredInfo(metadata.structured_info);
      }
      return;
    }

    // Mark this request as being processed
    loadedKeysRef.current.add(requestKey);

    // PMC or PM path
    if ((source === 'PM' || source === 'PMC') && currentPmcid) {
      // Fetch structured info (original logic)
      getStructuredInfo({
        pmcid: currentPmcid,
        pmid: metadata.pmid,
        ref_nctids: JSON.stringify(metadata.ref_nctids || []),
        page: metadata.page,
        index: metadata.index
      })
        .then(res => {
          if (isMounted) {
            setStructuredInfo(res.structured_info);
          }
        })
        .catch(() => {
          if (isMounted) {
            setStructuredInfo(null);
          }
          // Remove from loaded keys on error so it can be retried
          loadedKeysRef.current.delete(requestKey);
        });

      // --- Fetch Full Text HTML (added logic) ---
      getPmcFullTextHtml({ pmcid: currentPmcid })
        .then(htmlString => {
          if (isMounted) {
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
              setFullText(article.outerHTML);
            } else {
              setFullText(htmlString);
            }
            if (htmlString) {
              setFullTextExpanded(true);
            }
          }
        })
        .catch(() => {
            if (isMounted) {
              setFullText("<p>Error loading full text.</p>");
              setFullTextExpanded(true);
            }
        });
      // --- End of added logic ---
    }
    // CTG path
    else if (source === 'CTG' && nctId) {
      getCtgDetail({ nctId })
        .then(res => {
          if (isMounted) {
            setStructuredInfo(res.structured_info);
          }
        })
        .catch(() => {
          if (isMounted) {
            setStructuredInfo(null);
          }
          // Remove from loaded keys on error so it can be retried
          loadedKeysRef.current.delete(requestKey);
        });
    }

    return () => { 
      isMounted = false; 
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentPmcid, nctId, source, metadata]);

  // ChatBot/Glossary toggle
  const [showPanels, setShowPanels] = useState(true);

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'auto' });
  }, []);

  // Callback for ReferenceList to update selected reference state
  const handleActiveReferenceChange = (refInfo) => {
    setSelectedReferenceInfo(refInfo);
  };

  // Function to check if evidence text can be found in the relevant content
  const canHighlightEvidence = useCallback((evidenceText) => {
    if (typeof evidenceText !== 'string') return false;

    // Clean surrounding quotes (redundant if cleaned in ChatMessage, but safe)
    const cleanedText = evidenceText.trim().replace(/^['"]|['"]$/g, '');
    if (!cleanedText) return false;

    let contentToCheck = '';
    if (source === 'CTG') {
        // Check selected reference's full text if available
        if (selectedReferenceInfo && selectedReferenceInfo.fullText) {
            contentToCheck = selectedReferenceInfo.fullText;
        } else {
            // Cannot highlight if no reference selected/loaded
            return false;
        }
    } else { // PM/PMC source
        contentToCheck = fullText;
    }

    if (!contentToCheck) return false;

    // Case-insensitive check
    // Using includes for simplicity, could use regex for more complex matching if needed
    return contentToCheck.toLowerCase().includes(cleanedText.toLowerCase());
  }, [source, fullText, selectedReferenceInfo]); // Dependencies for the check

  const scrollToEvidence = (evidenceText) => {
    // Ensure evidenceText is a string before proceeding
    if (typeof evidenceText !== 'string' || !evidenceText) {
        console.warn("scrollToEvidence called with invalid text:", evidenceText);
        return;
    }
    // Clean text just in case it wasn't cleaned before calling
    const cleanedText = evidenceText.trim().replace(/^['"]|['"]$/g, '');
    if (!cleanedText) return;

    if (source === 'CTG' && selectedReferenceInfo) {
        // Attempt highlight in the selected reference's view
        referenceListRef.current?.highlightEvidenceInSelected?.(cleanedText);
    } else if (source !== 'CTG') {
        // Attempt highlight in the main full text view
        fullTextRef.current?.highlightEvidence?.(cleanedText);
    }
     // If source is CTG but no reference selected, highlighting isn't applicable to a specific text view
  };

  const ctgReferences = structuredInfo?.protocolSection?.referencesModule?.references || [];

  // --- Prepare CTG Metadata for display (logic remains the same) ---
  let ctgDetailsRowItems = [];
  if (source === 'CTG' && structuredInfo) {
    const studyType = structuredInfo.protocolSection?.designModule?.studyType;
    const referencesCount = ctgReferences.length;
    const status = structuredInfo.protocolSection?.statusModule?.overallStatus;
    const hasResults = structuredInfo.hasResultsData;

    if (studyType) ctgDetailsRowItems.push(studyType);
    if (referencesCount > 0) ctgDetailsRowItems.push(<strong key="ref">{referencesCount} references</strong>); else ctgDetailsRowItems.push('0 references');
    if (status) ctgDetailsRowItems.push(status);
    if (hasResults !== undefined) {
        if (hasResults) ctgDetailsRowItems.push(<strong key="res">has results</strong>); else ctgDetailsRowItems.push('no results');
    }
  }
  
  // Enhanced CTG metadata from basic data (search result level)
  let ctgEnhancedItems = [];
  if (source === 'CTG' && metadata) {
    // Add enhanced metadata from search results if available
    if (metadata.enrollment) {
      ctgEnhancedItems.push(`${metadata.enrollment} participants${metadata.enrollment_type ? ` (${metadata.enrollment_type})` : ''}`);
    }
    if (metadata.countries && metadata.countries.length > 0) {
      const countryText = metadata.countries.slice(0, 2).join(', ');
      ctgEnhancedItems.push(`${countryText}${metadata.countries.length > 2 ? ` +${metadata.countries.length - 2} more` : ''}`);
    }
    if (metadata.pmids && metadata.pmids.length > 0) {
      ctgEnhancedItems.push(`${metadata.pmids.length} related publication${metadata.pmids.length > 1 ? 's' : ''}`);
    }
  }
  
  const ctgOrganization = structuredInfo?.protocolSection?.identificationModule?.organization?.fullName;
  const ctgStartDate = structuredInfo?.protocolSection?.statusModule?.startDateStruct?.date;
  const ctgCompletionDateInfo = structuredInfo?.protocolSection?.statusModule?.completionDateStruct;
  const ctgCompletionDate = ctgCompletionDateInfo?.type === 'ACTUAL' ? ctgCompletionDateInfo?.date : null;
  // --- End CTG Metadata Preparation ---

  // Determine ChatBot props based on source and selected reference
  const getChatBotProps = () => {
      if (source === 'CTG') {
          if (selectedReferenceInfo) {
              // Case 2: CTG source, reference selected
              return {
                  paperId: selectedReferenceInfo.pmcid, // Keep for potential use
                  data: selectedReferenceInfo.fullText, // Use reference full text
                  source: 'PM', // Treat selected reference as a PubMed paper
                  relevantId: selectedReferenceInfo.pmcid, // ID is the PMCID
                  key: `chatbot-${selectedReferenceInfo.pmcid}`
              };
          } else {
              // Case 1: CTG source, no reference selected
              return {
                  paperId: nctId, // Keep for potential use
                  data: structuredInfo ? JSON.stringify(structuredInfo, null, 2) : null, // Use structured info (pretty-printed)
                  source: 'CTG', // Source is CTG
                  relevantId: nctId, // ID is the NCT ID
                  key: `chatbot-${nctId}`
              };
          }
      } else {
          // Default: PM/PMC source
          const currentPmcid = pmcid || metadata.pmcid; // Ensure we have the pmcid
          return {
              paperId: currentPmcid || paperId, // Use PMCID or PMID
              data: fullText, // Use main full text
              source: source || 'PM', // Use original source or default to PM
              relevantId: currentPmcid, // ID is the PMCID
              key: `chatbot-${currentPmcid || paperId}`
          };
      }
  };

  const chatBotProps = getChatBotProps();

  useEffect(() => {
    if (structuredInfo || fullText) {
      setIsDataLoaded(true);
    }
  }, [structuredInfo, fullText]);

  return (
    <><Header /> 
    <div className="px-6 py-8 max-w-screen-2xl mx-auto">
      
      <h1
        className="text-3xl font-bold text-black tracking-tight text-center cursor-pointer mb-6 hover:opacity-80 transition"
        onClick={() => navigate(-1)}
      >
        Clinical Trials Hub
      </h1>

      {/* Metadata card - PMC/PM */}
      {source !== 'CTG' && metadata.title !== 'No Title Available' && (
        <div className="bg-custom-bg-soft border border-custom-border p-5 rounded-2xl shadow-lg mb-8">
          <p className="text-xs text-custom-text-subtle mb-1">from PubMed</p>
          <h2 className="text-lg font-semibold text-custom-blue-deep mb-1">
            {metadata.title}
          </h2>
          {metadata.authors?.length > 0 && (
            <p className="text-sm text-custom-text-subtle mt-1">
              {metadata.authors.join(', ')}
            </p>
          )}
          <p className="text-sm text-custom-text mt-1">
            {metadata.journal && <span>{metadata.journal}</span>}
            {metadata.journal && metadata.pubDate && <span className="mx-1">|</span>}
            {metadata.pubDate && <span>{metadata.pubDate}</span>}
            {metadata.country && (
              <>
                <span className="mx-1">|</span>
                <span>{metadata.country}</span>
              </>
            )}
          </p>
          <p className="text-xs text-custom-text-subtle mt-1">
            {metadata.pmid && (
                <a
                    href={`https://pubmed.ncbi.nlm.nih.gov/${metadata.pmid}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-custom-blue hover:underline"
                >
                    {metadata.pmid}
                </a>
            )}
            {metadata.pmid && metadata.pmcid && <span className="mx-1">|</span>}
            {metadata.pmcid && (
                <a
                    href={`https://www.ncbi.nlm.nih.gov/pmc/articles/${metadata.pmcid}/`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-custom-blue hover:underline"
                >
                    {metadata.pmcid}
                </a>
            )}
          </p>
          
          {/* Enhanced PM metadata */}
          <div className="mt-2 space-y-1">
            {/* Publication Types */}
            {metadata.publication_types && metadata.publication_types.length > 0 && (
              <div className="flex items-center gap-1 flex-wrap">
                <span className="text-xs font-medium">Types:</span>
                {metadata.publication_types.slice(0, 3).map((type, idx) => (
                  <span key={idx} className="bg-purple-100 text-purple-800 px-2 py-0.5 rounded-full text-xs">
                    {type}
                  </span>
                ))}
                {metadata.publication_types.length > 3 && (
                  <span className="text-xs text-custom-text-subtle">+{metadata.publication_types.length - 3} more</span>
                )}
              </div>
            )}
            
            {/* Clinical Trial References */}
            {/* {metadata.ref_nctids && metadata.ref_nctids.length > 0 && (
              <div className="flex items-center gap-1">
                <span className="text-xs font-medium">Related Clinical Trials:</span>
                <span className="text-xs">
                  {metadata.ref_nctids.slice(0, 3).map((nctid, idx) => (
                    <span key={idx}>
                      <a
                        href={`https://clinicaltrials.gov/study/${nctid}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-custom-green hover:underline"
                      >
                        {nctid}
                      </a>
                      {idx < Math.min(metadata.ref_nctids.length, 3) - 1 && <span className="mx-1">|</span>}
                    </span>
                  ))}
                  {metadata.ref_nctids.length > 3 && (
                    <span className="text-custom-text-subtle"> +{metadata.ref_nctids.length - 3} more</span>
                  )}
                </span>
              </div>
            )} */}
          </div>
          
          {metadata.studyType && (
            <p className="text-sm text-custom-text mt-1">
              <strong>Study Type:</strong> {metadata.studyType}
            </p>
          )}
        </div>
      )}

      {/* Metadata card - CTG */}
      {source === 'CTG' && structuredInfo && (
        <div className="bg-custom-bg-soft border border-custom-border p-5 rounded-2xl shadow-lg mb-4">
          <p className="text-xs text-custom-text-subtle mb-1">from ClinicalTrials.gov</p>
          <h2 className="text-lg font-semibold text-custom-blue-deep mb-1">
              {structuredInfo.protocolSection?.identificationModule?.briefTitle || metadata.title}
          </h2>
          {(ctgOrganization || ctgStartDate || ctgCompletionDate) && (
            <p className="text-sm text-custom-text mt-1">
              {ctgOrganization}
              {ctgOrganization && (ctgStartDate || ctgCompletionDate) && <span className="mx-1">|</span>}
              {ctgStartDate && `Start: ${ctgStartDate}`}
              {ctgStartDate && ctgCompletionDate && <span className="mx-1">|</span>}
              {ctgCompletionDate && `Completion: ${ctgCompletionDate}`}
            </p>
          )}
          {ctgDetailsRowItems.length > 0 && (
            <p className="text-sm text-custom-text mt-1">
              {ctgDetailsRowItems.map((item, index) => (
            <React.Fragment key={index}>
              {item}
              {index < ctgDetailsRowItems.length - 1 && <span className="mx-1">|</span>}
            </React.Fragment>
              ))}
            </p>
          )}
          
          {/* Enhanced CTG metadata */}
          {ctgEnhancedItems.length > 0 && (
            <div className="mt-2">
              <div className="flex items-center gap-1 flex-wrap">
                <span className="text-xs font-medium">Study Info:</span>
                {ctgEnhancedItems.map((item, index) => (
                  <React.Fragment key={index}>
                    <span className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full">
                      {item}
                    </span>
                    {index < ctgEnhancedItems.length - 1 && <span className="mx-1">•</span>}
                  </React.Fragment>
                ))}
              </div>
              
              {/* Related publications with clickable links */}
              {metadata.pmids && metadata.pmids.length > 0 && (
                <div className="mt-1 flex items-center gap-1">
                  <span className="text-xs font-medium">Related Publications:</span>
                  <span className="text-xs">
                    {metadata.pmids.slice(0, 3).map((pmid, idx) => (
                      <span key={idx}>
                        <a
                          href={`https://pubmed.ncbi.nlm.nih.gov/${pmid}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-custom-blue hover:underline"
                        >
                          {pmid}
                        </a>
                        {idx < Math.min(metadata.pmids.length, 3) - 1 && <span className="mx-1">|</span>}
                      </span>
                    ))}
                    {metadata.pmids.length > 3 && (
                      <span className="text-custom-text-subtle"> +{metadata.pmids.length - 3} more</span>
                    )}
                  </span>
                </div>
              )}
              
              {/* Has Results indicator */}
              {metadata.has_results !== undefined && (
                <div className="mt-1 flex items-center gap-1">
                  <span className="text-xs font-medium">Results Available:</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    metadata.has_results ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                  }`}>
                    {metadata.has_results ? 'Yes' : 'No'}
                  </span>
                </div>
              )}
              {/* Clinical Trial References */}
              {metadata.ref_nctids && metadata.ref_nctids.length > 0 && (
                <div className="flex items-center gap-1">
                  <span className="text-xs font-medium">Related Clinical Trials:</span>
                  <span className="text-xs">
                    {metadata.ref_nctids.slice(0, 3).map((nctid, idx) => (
                      <span key={idx}>
                        <a
                          href={`https://clinicaltrials.gov/study/${nctid}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-custom-green hover:underline"
                        >
                          {nctid}
                        </a>
                        {idx < Math.min(metadata.ref_nctids.length, 3) - 1 && <span className="mx-1">|</span>}
                      </span>
                    ))}
                    {metadata.ref_nctids.length > 3 && (
                      <span className="text-custom-text-subtle"> +{metadata.ref_nctids.length - 3} more</span>
                    )}
                  </span>
                </div>
              )}
            </div>
          )}
          
          <p className="text-xs text-custom-text-subtle mt-1">
              <a
              href={`https://clinicaltrials.gov/study/${nctId}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-custom-blue hover:underline"
              >
              {nctId}
              </a>
          </p>
          </div>
        )}
       {/* ChatBot/Glossary + Structured Info */}
       {/* <div className="w-full max-w-4xl mx-auto mb-8"> */}
        <div className="w-full mb-8">
          {/* Toggle button */}
          <div className="flex justify-end mb-4">
            <button
              onClick={() => setShowPanels(prev => !prev)}
              className="text-sm text-custom-text-subtle hover:underline"
            >
              {showPanels ? 'Hide ChatBot & Glossary' : 'Show ChatBot & Glossary'}
            </button>
          </div>
          <div className="flex space-x-4">
            {showPanels && (
              <div className="basis-1/3 space-y-4">
                <div className="border border-custom-border rounded-2xl shadow-lg p-5 bg-white">
                  <div className="flex justify-between items-center border-b border-custom-border pb-2 mb-2">
                    <h2 className="text-xl font-semibold text-custom-blue-deep">ChatBot</h2>
                  </div>
                  {isDataLoaded ? (
                    <ChatBot
                      {...chatBotProps}
                      onEvidenceClick={scrollToEvidence}
                      canHighlightEvidence={canHighlightEvidence}
                    />
                  ) : (
                    <div>Loading...</div>
                  )}
                </div>
                <div className="border border-custom-border rounded-2xl shadow-lg p-5 bg-white">
                  <MeSHGlossary />
                </div>
              </div>
            )}
            <div className="flex-1 border border-custom-border rounded-2xl shadow-lg p-5 bg-white overflow-x-auto overflow-y-hidden">
              <h2 className="text-xl font-semibold text-custom-blue-deep border-b border-custom-border pb-2 mb-2">
                Structured Information
              </h2>
              {structuredInfo ? (
                <StructuredInfoTabs structuredInfo={structuredInfo} />
              ) : (
                <div className="flex justify-center items-center text-custom-text-subtle h-28 text-sm">
                  Loading structured info...
                </div>
              )}
            </div>
          </div>
        </div>

      {/* References (CTG) / Full Text (PMC) area */}
      <div className="border border-custom-border rounded-2xl shadow-lg p-5 mb-8 bg-white">
        {source === 'CTG' ? (
          // Pass the callback to ReferenceList
          <ReferenceList
            ref={referenceListRef}
            references={ctgReferences}
            onActiveReferenceChange={handleActiveReferenceChange} // Pass the callback
          />
        ) : ( // --- PMC Full Text Section ---
          <>
            <div className="flex justify-between items-center mb-2">
              {/* Corrected h2 tag structure */}
              <h2 className="text-xl font-semibold text-custom-blue-deep border-b border-custom-border pb-2">
                Full Text
              </h2>
              {fullText && (
                <button
                    onClick={() => setFullTextExpanded((prev) => !prev)}
                    className="p-1.5 text-custom-blue-deep rounded-full hover:bg-custom-blue-lightest transition-colors"
                    title={fullTextExpanded ? 'Collapse' : 'Expand'}
                >
                    {fullTextExpanded ? <ChevronsDownUp size={18} strokeWidth={2.5}/> : <ChevronsUpDown size={18} strokeWidth={2.5}/>}
                </button>
              )}
            </div>
            {fullTextExpanded && fullText ? (
              <FullText ref={fullTextRef} fullText={fullText} />
            ) : fullTextExpanded && !fullText ? (
                <div className="flex justify-center items-center text-custom-text-subtle h-28 text-sm">
                    Loading full text...
                </div>
            ) : null}
            {!fullText && !fullTextExpanded && (
                <p className="text-custom-text-subtle text-sm">Full text is collapsed or not available.</p>
            )}
          </>
        )}
      </div>

      <div className="flex justify-center -mt-3 px-2">
        <button
          // removed redundant 'border-2'
          className="border border-custom-blue-deep rounded-full p-1 text-custom-blue-deep text-sm font-semibold hover:bg-custom-blue-deep hover:text-white transition"
          onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
        >
          <ArrowUp />
        </button>
      </div>
    </div></>
  );
};

export default DetailPage;