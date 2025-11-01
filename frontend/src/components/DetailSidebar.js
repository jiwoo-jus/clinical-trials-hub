import PropTypes from 'prop-types';
import React, { useEffect, useState } from 'react';
import { PanelLeft, PanelRight, Settings } from 'lucide-react';

// Helper function to detect and linkify URLs and NCT IDs
const linkify = (text) => {
  if (!text) return text;

  const combinedRegex = /(https?:\/\/[^\s]+)|(NCT\d+)/g;
  const urlPattern = /^https?:\/\//;
  const nctPattern = /^NCT\d+$/;

  const parts = text.split(combinedRegex);

  return parts.map((part, index) => {
    if (!part) return null;

    if (part.match(urlPattern)) {
      return (
        <a
          key={`url-${index}`}
          href={part}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-600 hover:underline"
        >
          {part}
        </a>
      );
    } else if (part.match(nctPattern)) {
      const nctid = part;
      return (
        <a
          key={`nct-${index}`}
          href={`https://clinicaltrials.gov/study/${nctid}`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-600 hover:underline"
        >
          {nctid}
        </a>
      );
    } else {
      return part;
    }
  }).filter(Boolean);
};

const DetailSidebar = ({
  selectedResult,
  isVisible = true,
  defaultOpen = false,
  expandedWidth = '30%',
  collapsedWidth = '2rem',
  onToggle,
  otherSidebarOpen = false,
}) => {
  const OPTIONS = [
  { label: 'Brief Summary', value: 'BRIEF_SUMMARY' },
  { label: 'Study Details', value: 'STUDY_DETAILS' },
  { label: 'Interventions', value: 'INTERVENTIONS' },
  { label: 'Collaborators', value: 'COLLABORATORS' },
  { label: 'Investigators', value: 'INVESTIGATORS' },
  { label: 'Conditions', value: 'CONDITIONS' },
  { label: 'Keywords', value: 'KEYWORDS' },
  { label: 'Arm Groups', value: 'ARM_GROUPS' },
  { label: 'Eligibility Criteria', value: 'ELIGIBILITY_CRITERIA' },
  { label: 'Primary Outcomes', value: 'PRIMARY_OUTCOMES' },
  { label: 'Secondary Outcomes', value: 'SECONDARY_OUTCOMES' },
  { label: 'Publication Info', value: 'PUBLICATION_INFO' },
  { label: 'Additional Metadata', value: 'ADDITIONAL_METADATA' },
  { label: 'Abstract', value: 'ABSTRACT' }
  ];

  const PM_OPTIONS = [{ label: 'Publication Info', value: 'PUBLICATION_INFO' },
  { label: 'Additional Metadata', value: 'ADDITIONAL_METADATA' },
  { label: 'Abstract', value: 'ABSTRACT' },
  ];

  const CTG_OPTIONS = [
  { label: 'Brief Summary', value: 'BRIEF_SUMMARY' },
  { label: 'Study Details', value: 'STUDY_DETAILS' },
  { label: 'Interventions', value: 'INTERVENTIONS' },
  { label: 'Collaborators', value: 'COLLABORATORS' },
  { label: 'Investigators', value: 'INVESTIGATORS' },
  { label: 'Conditions', value: 'CONDITIONS' },
  { label: 'Keywords', value: 'KEYWORDS' },
  { label: 'Arm Groups', value: 'ARM_GROUPS' },
  { label: 'Eligibility Criteria', value: 'ELIGIBILITY_CRITERIA' },
  { label: 'Primary Outcomes', value: 'PRIMARY_OUTCOMES' },
  { label: 'Secondary Outcomes', value: 'SECONDARY_OUTCOMES' }
  ];

  const [isOpen, setIsOpen] = useState(defaultOpen);
  const [settingsOpen, setSettingsOpen] = useState(defaultOpen);
  const [filters, setFilters] = useState(OPTIONS.map(option => option.value));
 
  const handleToggleFilter = (value) => {
    setFilters((prev) =>
      prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value]
    );
  };
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkIfMobile = () => {
      setIsMobile(window.innerWidth <= 768);
    };

    checkIfMobile();
    window.addEventListener('resize', checkIfMobile);
    
    return () => window.removeEventListener('resize', checkIfMobile);
  }, []);

  useEffect(() => {
    if (selectedResult) {
      setIsOpen(true);
    }
  }, [selectedResult]);

  // Notify parent of sidebar state changes
  useEffect(() => {
    if (onToggle) {
      onToggle(isOpen);
    }
  }, [isOpen, onToggle]);

  // Don't render sidebar if not visible (no search results)
  if (!isVisible) {
    return null;
  }

  // Hide on mobile when other sidebar is open
  if (isMobile && otherSidebarOpen && !isOpen) {
    return null;
  }

  const toggleSidebar = () => {
    setIsOpen((prev) => !prev);
    if (settingsOpen) setSettingsOpen(false);
  };

  const toggleSettings = () => {
    setSettingsOpen((prev) => !prev);
    if (isOpen) setIsOpen(false);
  };

  const renderSettings = () => {  
    const half = Math.ceil(PM_OPTIONS.length / 2);
    const leftColumn = PM_OPTIONS.slice(0, half);
    const rightColumn = PM_OPTIONS.slice(half);

    const halfCTG = Math.ceil(CTG_OPTIONS.length / 2);
    const leftColumnCTG = CTG_OPTIONS.slice(0, halfCTG);
    const rightColumnCTG = CTG_OPTIONS.slice(halfCTG);

      return (
        <div>
          <div className="mb-4">
              <div className="bg-custom-bg-soft rounded-xl p-4 border border-custom-border">
                <h4 className="font-semibold mb-3 text-custom-text">CTG Result Filters</h4>
                <div className="grid grid-cols-2 gap-x-8">
                  {[leftColumnCTG, rightColumnCTG].map((column, colIndex) => (
                    <div key={colIndex} className="space-y-2">
                      {column.map(option => (
                        <label
                          key={option.value}
                          className="flex items-center justify-between cursor-pointer"
                        >
                          <div className="flex items-center gap-2">
                            <input
                              type="checkbox"
                              id={option.value}
                              checked={filters.includes(option.value)}
                              onChange={() => handleToggleFilter(option.value)}
                              className="accent-custom-blue w-4 h-4 rounded border-gray-300 focus:ring-2 focus:ring-custom-blue"
                            />
                            <span className="text-sm text-custom-text">{option.label}</span>
                          </div>
                        </label>
                      ))}
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-custom-bg-soft rounded-xl p-4 border mt-3 border-custom-border">
                <h4 className="font-semibold mb-3 text-custom-text">PM Result Filters</h4>
                <div className="grid grid-cols-2 gap-x-8">
                  {[leftColumn, rightColumn].map((column, colIndex) => (
                    <div key={colIndex} className="space-y-2">
                      {column.map(option => (
                        <label
                          key={option.value}
                          className="flex items-center justify-between cursor-pointer"
                        >
                          <div className="flex items-center gap-2">
                            <input
                              type="checkbox"
                              id={option.value}
                              checked={filters.includes(option.value)}
                              onChange={() => handleToggleFilter(option.value)}
                              className="accent-custom-blue w-4 h-4 rounded border-gray-300 focus:ring-2 focus:ring-custom-blue"
                            />
                            <span className="text-sm text-custom-text">{option.label}</span>
                          </div>
                        </label>
                      ))}
                    </div>
                  ))}
                </div>
              </div>
              <button
                onClick={toggleSettings}
                className="px-3 py-1 mt-3 bg-custom-blue text-white rounded-lg font-semibold shadow-sm hover:bg-custom-blue-hover disabled:opacity-50 transition"
              >
                Apply Filters
              </button>
            
          </div>
        </div>
      )
  }


  const renderContent = () => {
    if (!selectedResult) {
      return <p className="text-sm text-gray-500">Select a result to view details.</p>;
    }
    
    console.log('[DetailSidebar] selectedResult:', selectedResult);
    console.log('[DetailSidebar] source:', selectedResult.source);
    console.log('[DetailSidebar] structured_info:', selectedResult?.structured_info);
    
    // Handle PM or PMC source (including MERGED with PM focus)
    if (selectedResult.source === 'PM' || selectedResult.source === 'PMC') {
      if (selectedResult.type === 'MERGED') selectedResult = selectedResult.pm_data;
      const abstract = selectedResult.abstract;
      if (!abstract) {
        return <p className="text-sm text-gray-500">No abstract available.</p>;
      }
      return (
        <div>

          {/* Publication Info */}
          { filters.includes('PUBLICATION_INFO') &&
          <div className="mb-4">
            <h4 className="font-semibold text-base mb-2">Publication Info</h4>
            <div className="space-y-2 text-sm">
              {selectedResult.journal && (
                <div>
                  <span className="font-medium">Journal:</span>
                  <span className="ml-2">{selectedResult.journal}</span>
                </div>
              )}
              {selectedResult.issue && (
                <div>
                  <span className="font-medium">Issue:</span>
                  <span className="ml-2">{selectedResult.issue}</span>
                </div>
              )}
              {selectedResult.volume && (
                <div>
                  <span className="font-medium">Volume:</span>
                  <span className="ml-2">{selectedResult.volume}</span>
                </div>
              )}
              {selectedResult.authors && selectedResult.authors.length > 0 && (
                <div>
                  <span className="font-medium">Authors:</span>
                  <span className="ml-2">{selectedResult.authors.join(', ')}</span>
                </div>
              )}
              {selectedResult.pubDate && (
                <div>
                  <span className="font-medium">Published:</span>
                  <span className="ml-2">{new Date(selectedResult.pubDate).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })}</span>
                </div>
              )}
              {selectedResult.pmid && (
                <div>
                  <span className="font-medium">PMID:</span>
                  <a
                    href={`https://pubmed.ncbi.nlm.nih.gov/${selectedResult.pmid}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="ml-2 text-custom-blue hover:underline"
                  >
                    {selectedResult.pmid}
                  </a>
                </div>
              )}
              {selectedResult.pmcid && (
                <div>
                  <span className="font-medium">PMCID:</span>
                  <a
                    href={`https://pmc.ncbi.nlm.nih.gov/articles/${selectedResult.pmcid}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="ml-2 text-custom-blue hover:underline"
                  >
                    {selectedResult.pmcid}
                  </a>
                </div>
              )}
              {selectedResult.doi && (
                <div>
                  <span className="font-medium">DOI:</span>
                  <a
                    href={`https://doi.org/${selectedResult.doi}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="ml-2 text-custom-blue hover:underline"
                  >
                    {selectedResult.doi}
                  </a>
                </div>
              )}
              
              {selectedResult.nctid && (
                <div>
                  <span className="font-medium">Related Trial:</span>
                  <a
                    href={`https://clinicaltrials.gov/study/${selectedResult.nctid}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="ml-2 text-custom-green hover:underline"
                  >
                    {selectedResult.nctid}
                  </a>
                </div>
              )}
            </div>
          </div> }

          
          {/* Additional PM Metadata */}
          {(selectedResult.ref_nctids || selectedResult.mesh_headings || selectedResult.keywords || selectedResult.publication_types || selectedResult.country) &&  filters.includes('ADDITIONAL_METADATA') && (
            <div className="mb-4">
              <h4 className="font-semibold text-base mb-2">Additional Metadata</h4>
              <div className="space-y-2 text-sm">
                {selectedResult.ref_nctids && selectedResult.ref_nctids.length > 0 && (
                  <div>
                    <span className="font-medium">Related Clinical Trials:</span>
                    <div className="ml-2 mt-1">
                      <span className="text-sm">
                        {selectedResult.ref_nctids.map((nctid, idx) => (
                          <span key={idx}>
                            <a
                              href={`https://clinicaltrials.gov/study/${nctid}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-custom-green hover:underline"
                            >
                              {nctid}
                            </a>
                            {idx < selectedResult.ref_nctids.length - 1 && <span className="mx-1">|</span>}
                          </span>
                        ))}
                      </span>
                    </div>
                  </div>
                )}

                {/* Publication Types */}
                {selectedResult.publication_types && selectedResult.publication_types.length > 0 && (
                  <div>
                    <span className="font-medium">Publication Types:</span>
                    <div className="ml-2 mt-1 flex flex-wrap gap-1">
                      {selectedResult.publication_types.map((type, idx) => (
                        <span key={idx} className="bg-purple-100 text-purple-800 text-xs px-2 py-1 rounded-full">
                          {type}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Country */}
                {selectedResult.country && (
                  <div>
                    <span className="font-medium">Country:</span>
                    <span className="ml-2">{selectedResult.country}</span>
                  </div>
                )}

                {/* MeSH Headings */}
                {selectedResult.mesh_headings && selectedResult.mesh_headings.length > 0 && (
                  <div>
                    <span className="font-medium">MeSH Headings:</span>
                    <div className="ml-2 mt-1 flex flex-wrap gap-1">
                      {selectedResult.mesh_headings.slice(0, 10).map((mesh, idx) => (
                        <span key={idx} className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full">
                          {typeof mesh === 'string' ? mesh : mesh.descriptor || 'Unknown'}
                        </span>
                      ))}
                      {selectedResult.mesh_headings.length > 10 && (
                        <span className="text-xs text-gray-500 px-2 py-1">
                          +{selectedResult.mesh_headings.length - 10} more
                        </span>
                      )}
                    </div>
                  </div>
                )}

                {/* Keywords */}
                {selectedResult.keywords && selectedResult.keywords.length > 0 && (
                  <div>
                    <span className="font-medium">Keywords:</span>
                    <div className="ml-2 mt-1 flex flex-wrap gap-1">
                      {selectedResult.keywords.slice(0, 8).map((keyword, idx) => (
                        <span key={idx} className="bg-gray-100 text-gray-700 text-xs px-2 py-1 rounded-full">
                          {keyword}
                        </span>
                      ))}
                      {selectedResult.keywords.length > 8 && (
                        <span className="text-xs text-gray-500 px-2 py-1">
                          +{selectedResult.keywords.length - 8} more
                        </span>
                      )}
                    </div>
                  </div>
                )}

                {/* study type */}
                {selectedResult.study_type && (
                  <div className="pt-1">
                    <span className="font-medium">Study Type:</span>
                    <span className="ml-2">{selectedResult.study_type}</span>
                  </div>
                )}

                {/* allocation */}
                {selectedResult.design_allocation && (
                  <div>
                    <span className="font-medium">Design Allocation:</span>
                    <span className="ml-2">{selectedResult.design_allocation}</span>
                  </div>
                )}

                {/* observational model */}
                {selectedResult.observational_model && (
                  <div>
                    <span className="font-medium">Observational Model:</span>
                    <span className="ml-2">{selectedResult.observational_model}</span>
                  </div>
                )}

                {/* phase */}
                {selectedResult.phase && (
                  <div>
                    <span className="font-medium">Phase:</span>
                    <span className="ml-2">{selectedResult.phase}</span>
                  </div>
                )}

                {/* Grants */}
                {selectedResult.grants && selectedResult.grants.length > 0 && (
                  <div>
                    <span className="font-medium">Grants:</span>
                    <div className="ml-2 mt-1 flex flex-wrap gap-1">
                      {selectedResult.grants.slice(0, 8).map((grant, idx) => (
                        <span key={idx} className="bg-purple-100 text-purple-700 text-xs px-2 py-1 rounded-full">
                          {grant.agency}, {grant.country}
                        </span>
                      ))}
                      {selectedResult.grants.length > 5 && (
                        <span className="text-xs text-gray-500 px-2 py-1">
                          +{selectedResult.grants.length - 8} more
                        </span>
                      )}
                    </div>
                  </div>
                )}

              </div>
            </div>
          )}

          
          {filters.includes('ABSTRACT') && Object.entries(abstract).map(([key, value]) => (
    
            <div key={key} className="mb-4">
              <span className="font-semibold block text-base mb-2">{key}</span>
              <span className="block text-sm leading-relaxed">{linkify(value)}</span>
            </div> 
          ))}
        </div>
      );
    } 
    // Handle CTG source (including MERGED with CTG focus)
    else if (selectedResult.source === 'CTG') {
      const detailedInfo = selectedResult?.structured_info;
      const hasDetailedInfo = detailedInfo && Object.keys(detailedInfo).length > 0;
      
      console.log('[DetailSidebar] CTG detailedInfo:', detailedInfo);
      console.log('[DetailSidebar] hasDetailedInfo:', hasDetailedInfo);
      const details = selectedResult.study_details
      if (selectedResult.type === 'MERGED'){
        selectedResult = selectedResult.ctg_data;
      }
      if (details) {
        selectedResult.study_details = details;
        selectedResult.primary_outcomes = selectedResult.study_details.outcomesModule?.primaryOutcomes?.map(outcome => outcome.measure);
        selectedResult.secondary_outcomes = selectedResult.study_details.outcomesModule?.secondaryOutcomes?.map(outcome => outcome.measure);
        selectedResult.groups = selectedResult.study_details.armsInterventionsModule?.armGroups?.map(group => `${group.type?.replace('_', ' ')}: ${group.label}`);
      }

      // Display basic info when structured_info is unavailable or empty
      if (!hasDetailedInfo) {
        return (
          <div className="space-y-4">

            {/* Study Details from basic data */}
            { filters.includes('STUDY_DETAILS') && 
            <div className="mb-4">
              <h4 className="font-semibold text-base mb-2">Study Details</h4>
              <div className="space-y-2 text-sm">
                {selectedResult.status && (
                  <div>
                    <span className="font-medium">Status:</span>
                    <span className="ml-2">{selectedResult.status}</span>
                  </div>
                )}
                {selectedResult.phase && (
                  <div>
                    <span className="font-medium">Phase:</span>
                    <span className="ml-2">{selectedResult.phase}</span>
                  </div>
                )}
                {selectedResult.lead_sponsor && (
                  <div>
                    <span className="font-medium">Lead Sponsor:</span>
                    <span className="ml-2">{selectedResult.lead_sponsor}</span>
                  </div>
                )}
                
                {/* Study Type */}
                {selectedResult.study_type && (
                  <div>
                    <span className="font-medium">Study Type:</span>
                    <span className="ml-2">{selectedResult.study_type}</span>
                  </div>
                )}

                {/* Enhanced CTG metadata - Countries */}
                {selectedResult.countries && selectedResult.countries.length > 0 && (
                  <div>
                    <span className="font-medium">Countries:</span>
                    <span className="ml-2">
                      {selectedResult.countries.slice(0, 3).join(', ')}
                      {selectedResult.countries.length > 3 && ` +${selectedResult.countries.length - 3} more`}
                    </span>
                  </div>
                )}

                {/* Has Results indicator */}
                {selectedResult.has_results !== undefined && (
                  <div>
                    <span className="font-medium">Has Results:</span>
                    <span className={`ml-2 px-2 py-1 rounded-full text-xs ${
                      selectedResult.has_results ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                    }`}>
                      {selectedResult.has_results ? 'Yes' : 'No'}
                    </span>
                  </div>
                )}

                {/* Enrollment information */}
                {selectedResult.enrollment && (
                  <div>
                    <span className="font-medium">Enrollment:</span>
                    <span className="ml-2">
                      {selectedResult.enrollment}
                      {selectedResult.enrollment_type && ` (${selectedResult.enrollment_type})`}
                    </span>
                  </div>
                )}

                {/* Related publications */}
                {selectedResult.pmids && selectedResult.pmids.length > 0 && (
                  <div>
                    <span className="font-medium">Related Publications:</span>
                    <div className="ml-2 mt-1">
                      <span className="text-sm">
                        {selectedResult.pmids.slice(0, 3).map((pmid, idx) => (
                          <span key={idx}>
                            <a
                              href={`https://pubmed.ncbi.nlm.nih.gov/${pmid}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-custom-blue hover:underline"
                            >
                              {pmid}
                            </a>
                            {idx < Math.min(selectedResult.pmids.length, 3) - 1 && <span className="mx-1">|</span>}
                          </span>
                        ))}
                        {selectedResult.pmids.length > 3 && (
                          <span className="text-custom-text-subtle"> +{selectedResult.pmids.length - 3} more</span>
                        )}
                      </span>
                    </div>
                  </div>
                )}
                
                {/* Official Title if different from brief title */}
                {selectedResult.official_title && selectedResult.official_title !== selectedResult.title && (
                  <div>
                    <span className="font-medium">Official Title:</span>
                    <span className="ml-2 text-xs">{selectedResult.official_title}</span>
                  </div>
                )}
                
                {/* Study Duration */}
                {(selectedResult.start_date || selectedResult.completion_date || selectedResult.primary_completion_date) && (
                  <div>
                    <span className="font-medium">Study Period:</span>
                    <span className="ml-2">
                      {selectedResult.start_date && new Date(selectedResult.start_date).toLocaleDateString('en-US', { year: 'numeric', month: 'short' })}
                      {selectedResult.start_date && (selectedResult.completion_date || selectedResult.primary_completion_date) && ' - '}
                      {(selectedResult.completion_date || selectedResult.primary_completion_date) && 
                        new Date(selectedResult.completion_date || selectedResult.primary_completion_date).toLocaleDateString('en-US', { year: 'numeric', month: 'short' })
                      }
                    </span>
                  </div>
                )}
              </div>
            </div>
            }

            {/* Conditions from basic data */}
            
            { filters.includes('CONDITIONS') && selectedResult.conditions && selectedResult.conditions.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-base mb-2">Conditions</h4>
                <div className="flex flex-wrap gap-1">
                  {selectedResult.conditions.map((condition, idx) => (
                    <span key={idx} className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full">
                      {condition}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Interventions */}
            
            {filters.includes('INTERVENTIONS') && selectedResult.intervention_names && selectedResult.intervention_names.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-base mb-2">Interventions</h4>
                <div className="space-y-1">
                  {selectedResult.intervention_names.map((intervention, idx) => (
                    <div key={idx} className="border-l-2 border-blue-200 pl-3">
                      <p className="text-sm">{intervention}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
            

            {/* Collaborators */}
            
            {filters.includes('COLLABORATORS') &&  selectedResult.collaborators && selectedResult.collaborators.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-base mb-2">Collaborators</h4>
                <div className="flex flex-wrap gap-1">
                  {selectedResult.collaborators.map((collaborator, idx) => (
                    <span key={idx} className="bg-gray-100 text-gray-700 text-xs px-2 py-1 rounded-full">
                      {collaborator}
                    </span>
                  ))}
                </div>
              </div>
            )}
            

            {/* Investigators */}
            
            { filters.includes('INVESTIGATORS') && selectedResult.study_details.contactsLocationsModule.overallOfficials && selectedResult.study_details.contactsLocationsModule.overallOfficials.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-base mb-2">Investigators</h4>
                <div className="flex flex-wrap gap-1">
                  {selectedResult.study_details.contactsLocationsModule.overallOfficials.map((collaborator, idx) => (
                    <span key={idx} className="bg-purple-100 text-purple-700 text-xs px-2 py-1 rounded-full">
                      {collaborator.name}, {collaborator.affiliation}
                    </span>
                  ))}
                </div>
              </div>
            )}
            
            {/* Keywords from basic data */}
            
            { filters.includes('KEYWOWRDS') && selectedResult.keywords && selectedResult.keywords.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-base mb-2">Keywords</h4>
                <div className="flex flex-wrap gap-1">
                  {selectedResult.keywords.map((keyword, idx) => (
                    <span key={idx} className="bg-gray-100 text-gray-700 text-xs px-2 py-1 rounded-full">
                      {keyword}
                    </span>
                  ))}
                </div>
              </div>
            )}
            

             {/* Arm Groups */}
              
            { filters.includes('ARM_GROUPS') && selectedResult.groups && selectedResult.groups.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-base mb-2">Arm Groups</h4>
                <div className="space-y-1">
                  {selectedResult.groups.map((group, idx) => (
                    <div key={idx} className="border-l-2 border-purple-200 pl-3">
                      <p className="text-sm">{group}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
            

            {/* Eligibility criteria */}
            { filters.includes('ELIGIBILITY_CRITERIA') && 
            <div className="mb-4">
              <h4 className="font-semibold text-base mb-2">Eligibility Criteria</h4>
              <div className="space-y-2 text-sm">
                {selectedResult.study_details.eligibilityModule.stdAges && (
                  <div>
                    <span className="font-medium">Age Group(s):</span>
                    <span className="ml-2">{selectedResult.study_details.eligibilityModule.stdAges.join(', ').replace('_', ' ')}</span>
                  </div>
                )}
                {selectedResult.study_details.eligibilityModule.sex && (
                  <div>
                    <span className="font-medium">Sexes:</span>
                    <span className="ml-2">{selectedResult.study_details.eligibilityModule.sex}</span>
                  </div>
                )}
                {selectedResult.study_details.eligibilityModule.minimumAge && selectedResult.study_details.eligibilityModule.maximumAge && (
                  <div>
                    <span className="font-medium">Age Range:</span>
                    <span className="ml-2">{selectedResult.study_details.eligibilityModule.minimumAge} to {selectedResult.study_details.eligibilityModule.maximumAge}</span>
                  </div>
                )}

                {/* Enrollment information */}
                {selectedResult.study_details.eligibilityModule.healthyVolunteers && (
                  <div>
                    <span className="font-medium">Accepts Healthy Volunteers?</span>
                    <span className="ml-2">
                      {selectedResult?.study_details?.eligibilityModule?.healthyVolunteers === true ? "Yes" : "No"}
                    </span>
                  </div>
                )}
              </div>
            </div>
            } 

            {/* Primary Outcomes from basic data */}
            
            { filters.includes('PRIMARY_OUTCOMES') && selectedResult.primary_outcomes && selectedResult.primary_outcomes.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-base mb-2">Primary Outcomes</h4>
                <div className="space-y-1">
                  {selectedResult.primary_outcomes.map((outcome, idx) => (
                    <div key={idx} className="border-l-2 border-blue-200 pl-3">
                      <p className="text-sm">{outcome}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
            

            {/* Secondary Outcomes from basic data */}
            
            { filters.includes('SECONDARY_OUTCOMES') && selectedResult.secondary_outcomes && selectedResult.secondary_outcomes.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-base mb-2">Secondary Outcomes</h4>
                <div className="space-y-1">
                  {selectedResult.secondary_outcomes.slice(0, 3).map((outcome, idx) => (
                    <div key={idx} className="border-l-2 border-gray-200 pl-3">
                      <p className="text-sm">{outcome}</p>
                    </div>
                  ))}
                  {selectedResult.secondary_outcomes.length > 3 && (
                    <p className="text-xs text-gray-500 italic">
                      +{selectedResult.secondary_outcomes.length - 3} more secondary outcomes
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* Brief Summary from basic data */}
            
            {filters.includes('BRIEF_SUMMARY') && selectedResult.brief_summary && (
              <div className="mb-4">
                <h4 className="font-semibold text-base mb-2">Brief Summary</h4>
                <p className="text-sm leading-relaxed">{linkify(selectedResult.brief_summary)}</p>
              </div>
            )}
            
          </div>
        );
      }

      // Display detailed info when structured_info is available
      return (
        <div className="space-y-4">
          {/* Brief Summary */}
          {detailedInfo.briefSummary && (
            <div className="mb-4">
              <h4 className="font-semibold text-base mb-2">Brief Summary</h4>
              <p className="text-sm leading-relaxed">{linkify(detailedInfo.briefSummary)}</p>
            </div>
          )}

          {/* Study Details */}
          <div className="mb-4">
            <h4 className="font-semibold text-base mb-2">Study Details</h4>
            <div className="space-y-2 text-sm">
              {detailedInfo.overallStatus && (
                <div>
                  <span className="font-medium">Status:</span>
                  <span className="ml-2">{detailedInfo.overallStatus}</span>
                </div>
              )}
              {detailedInfo.phase && (
                <div>
                  <span className="font-medium">Phase:</span>
                  <span className="ml-2">{detailedInfo.phase}</span>
                </div>
              )}
              {detailedInfo.leadSponsor && (
                <div>
                  <span className="font-medium">Lead Sponsor:</span>
                  <span className="ml-2">{detailedInfo.leadSponsor}</span>
                </div>
              )}
              
              {/* Enhanced Study Design Information */}
              {detailedInfo.studyType && (
                <div>
                  <span className="font-medium">Study Type:</span>
                  <span className="ml-2">{detailedInfo.studyType}</span>
                </div>
              )}
              
              {detailedInfo.primaryPurpose && (
                <div>
                  <span className="font-medium">Primary Purpose:</span>
                  <span className="ml-2">{detailedInfo.primaryPurpose}</span>
                </div>
              )}
              
              {detailedInfo.allocation && (
                <div>
                  <span className="font-medium">Allocation:</span>
                  <span className="ml-2">{detailedInfo.allocation}</span>
                </div>
              )}
              
              {detailedInfo.interventionModel && (
                <div>
                  <span className="font-medium">Intervention Model:</span>
                  <span className="ml-2">{detailedInfo.interventionModel}</span>
                </div>
              )}
              
              {detailedInfo.masking && (
                <div>
                  <span className="font-medium">Masking:</span>
                  <span className="ml-2">{detailedInfo.masking}</span>
                </div>
              )}
              
              {/* Enrollment Information */}
              {detailedInfo.enrollmentCount && (
                <div>
                  <span className="font-medium">Enrollment:</span>
                  <span className="ml-2">{detailedInfo.enrollmentCount}{detailedInfo.enrollmentType ? ` (${detailedInfo.enrollmentType})` : ''}</span>
                </div>
              )}
              
              {/* Eligibility Criteria Summary */}
              {(detailedInfo.eligibleSex || detailedInfo.minimumAge || detailedInfo.maximumAge) && (
                <div>
                  <span className="font-medium">Eligibility:</span>
                  <span className="ml-2">
                    {detailedInfo.eligibleSex && `${detailedInfo.eligibleSex}`}
                    {detailedInfo.minimumAge && `, Ages ${detailedInfo.minimumAge}`}
                    {detailedInfo.maximumAge && ` to ${detailedInfo.maximumAge}`}
                  </span>
                </div>
              )}
              
              {/* Study Duration */}
              {(detailedInfo.startDate || detailedInfo.completionDate || detailedInfo.primaryCompletionDate) && (
                <div>
                  <span className="font-medium">Study Period:</span>
                  <span className="ml-2">
                    {detailedInfo.startDate && new Date(detailedInfo.startDate).toLocaleDateString('en-US', { year: 'numeric', month: 'short' })}
                    {detailedInfo.startDate && (detailedInfo.completionDate || detailedInfo.primaryCompletionDate) && ' - '}
                    {(detailedInfo.completionDate || detailedInfo.primaryCompletionDate) && 
                      new Date(detailedInfo.completionDate || detailedInfo.primaryCompletionDate).toLocaleDateString('en-US', { year: 'numeric', month: 'short' })
                    }
                  </span>
                </div>
              )}
              
              {/* Locations */}
              {detailedInfo.locations && detailedInfo.locations.length > 0 && (
                <div>
                  <span className="font-medium">Locations:</span>
                  <div className="ml-2 mt-1">
                    {detailedInfo.locations.slice(0, 3).map((location, idx) => (
                      <div key={idx} className="text-xs bg-gray-100 px-2 py-1 rounded mb-1 inline-block mr-1">
                        {location.city && `${location.city}, `}{location.state && `${location.state}, `}{location.country}
                      </div>
                    ))}
                    {detailedInfo.locations.length > 3 && (
                      <span className="text-xs text-gray-500">+{detailedInfo.locations.length - 3} more locations</span>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Conditions */}
          {detailedInfo.conditions && detailedInfo.conditions.length > 0 && (
            <div className="mb-4">
              <h4 className="font-semibold text-base mb-2">Conditions</h4>
              <div className="flex flex-wrap gap-1">
                {detailedInfo.conditions.map((condition, idx) => (
                  <span key={idx} className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full">
                    {condition}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Interventions from detailed info */}
          {detailedInfo.interventions && detailedInfo.interventions.length > 0 && (
            <div className="mb-4">
              <h4 className="font-semibold text-base mb-2">Interventions</h4>
              <div className="space-y-2">
                {detailedInfo.interventions.map((intervention, idx) => (
                  <div key={idx} className="border-l-2 border-blue-200 pl-3">
                    <p className="text-sm font-medium">{intervention.name}</p>
                    {intervention.description && (
                      <p className="text-xs text-gray-600 mt-1">{intervention.description}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Collaborators from detailed info */}
          {detailedInfo.collaborators && detailedInfo.collaborators.length > 0 && (
            <div className="mb-4">
              <h4 className="font-semibold text-base mb-2">Collaborators</h4>
              <div className="flex flex-wrap gap-1">
                {detailedInfo.collaborators.map((collaborator, idx) => (
                  <span key={idx} className="bg-gray-100 text-gray-700 text-xs px-2 py-1 rounded-full">
                    {collaborator}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Keywords */}
          {detailedInfo.keywords && detailedInfo.keywords.length > 0 && (
            <div className="mb-4">
              <h4 className="font-semibold text-base mb-2">Keywords</h4>
              <div className="flex flex-wrap gap-1">
                {detailedInfo.keywords.map((keyword, idx) => (
                  <span key={idx} className="bg-gray-100 text-gray-700 text-xs px-2 py-1 rounded-full">
                    {keyword}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Primary Outcomes */}
          {detailedInfo.primaryOutcomes && detailedInfo.primaryOutcomes.length > 0 && (
            <div className="mb-4">
              <h4 className="font-semibold text-base mb-2">Primary Outcomes</h4>
              <div className="space-y-2">
                {detailedInfo.primaryOutcomes.map((outcome, idx) => (
                  <div key={idx} className="border-l-2 border-blue-200 pl-3">
                    {outcome.measure && (
                      <p className="text-sm font-medium mb-1">{outcome.measure}</p>
                    )}
                    {outcome.description && (
                      <p className="text-xs text-gray-600">{linkify(outcome.description)}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Secondary Outcomes */}
          {detailedInfo.secondaryOutcomes && detailedInfo.secondaryOutcomes.length > 0 && (
            <div className="mb-4">
              <h4 className="font-semibold text-base mb-2">Secondary Outcomes</h4>
              <div className="space-y-2">
                {detailedInfo.secondaryOutcomes.slice(0, 3).map((outcome, idx) => (
                  <div key={idx} className="border-l-2 border-gray-200 pl-3">
                    {outcome.measure && (
                      <p className="text-sm font-medium mb-1">{outcome.measure}</p>
                    )}
                    {outcome.description && (
                      <p className="text-xs text-gray-600">{linkify(outcome.description)}</p>
                    )}
                  </div>
                ))}
                {detailedInfo.secondaryOutcomes.length > 3 && (
                  <p className="text-xs text-gray-500 italic">
                    +{detailedInfo.secondaryOutcomes.length - 3} more secondary outcomes
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Study Link */}
          <div className="mt-4 pt-4 border-t border-gray-200">
            <a
              href={`https://clinicaltrials.gov/study/${detailedInfo.nctId || selectedResult.nctid || selectedResult.id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:underline text-sm font-medium"
            >
              View full study on ClinicalTrials.gov →
            </a>
          </div>

          {/* Enhanced info indicator */}
          <div className="mt-2 p-2 bg-green-50 border border-green-200 rounded">
            <p className="text-xs text-green-700">
              ✓ Enhanced details loaded from ClinicalTrials.gov API
            </p>
          </div>
        </div>
      );
    } else {
      return <p className="text-sm text-gray-500">Details not available.</p>;
    }
  };

  const getTitle = () => {
    if (!selectedResult || !isOpen) return null;

    if ((selectedResult.source === 'PM' || selectedResult.source === 'PMC') && selectedResult.abstract) {
      return 'Abstract';
    } else if (selectedResult.source === 'CTG') {
      return 'Study Details';
    }
    return null;
  };

  const title = getTitle();

  return (
    <div
      className={`bg-white shadow-lg border-l border-gray-200 transition-all duration-300 ease-in-out ${isOpen ? 'rounded-r-2xl' : 'rounded-l-lg'} flex-shrink-0 ${
        isMobile ? (isOpen ? 'fixed right-0 top-0 z-50' : 'fixed right-0 top-16 z-50') : 'sticky top-0'
      }`}
      style={{
        width: isOpen || settingsOpen ? 
          (isMobile ? '100%' : expandedWidth) : 
          collapsedWidth,
        height: isMobile && !isOpen ? 'auto' : 
          isMobile && isOpen ? '100vh' : 
          'calc(100vh - 64px)'
      }}
    >
      {/* Header Section */}
      <div className={`flex items-center ${isOpen ? 'justify-between' : 'justify-center'} p-2 ${settingsOpen ? 'border-b-0' : 'border-b'} border-gray-200`}>
        {isOpen && title && (
          <h3 className="font-bold text-lg ml-2">{title}</h3>
        )}
        {isOpen && !title && <div />}

        {!settingsOpen && (
        <button
          type="button"
          aria-controls="sidebar-drawer"
          aria-expanded={isOpen}
          className="p-1 text-primary-44 hover:text-primary-100 duration-short ease-curve-a cursor-pointer transition-colors"
          aria-label="Toggle navigation sidebar"
          onClick={toggleSidebar}
        >
          {isOpen ? <PanelLeft size={18} /> : <PanelRight size={18} />}
        </button>
        )}
      </div>

      {/* Footer Section */}
      <div className={`flex items-center ${settingsOpen ? 'justify-between' : 'justify-center'} p-2 ${isOpen ? 'border-b-0' : 'border-b'}  border-gray-200`}>
        {settingsOpen && (
          <h3 className="font-bold text-lg ml-2">Study Detail Settings</h3>
        )}
        {settingsOpen && <div />}
        {!isOpen && (
          <button
            className="p-1 text-primary-44 hover:text-primary-100 duration-short ease-curve-a cursor-pointer transition-colors"
            type="button"
            aria-label="Open settings"
            aria-expanded={isOpen}
            onClick={toggleSettings}
          >
            <Settings size={18} />
          </button>
        )}
      </div>

      {isOpen && (
        <div 
          className="px-4 py-2 text-sm text-gray-700" 
          style={{ 
            height: isMobile ? 'calc(100vh - 41px)' : 'calc(100vh - 64px - 41px)', 
            overflowY: 'auto' 
          }}
        >
          {renderContent()}
        </div>
      )}

      {settingsOpen && (
        <div className="px-4 py-2 text-sm text-gray-700 " style={{ height: 'calc(100vh - 41px)' }}>
          {renderSettings()}
        </div>
      )}
    </div>
  );
};

DetailSidebar.propTypes = {
  selectedResult: PropTypes.object,
  isVisible: PropTypes.bool,
  defaultOpen: PropTypes.bool,
  expandedWidth: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  collapsedWidth: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  onToggle: PropTypes.func,
  otherSidebarOpen: PropTypes.bool,
};

export default DetailSidebar;
