import { Building2, Calendar, ChevronDown, ToggleLeft, ToggleRight, Clock, Earth, Eye, User } from 'lucide-react';
import PropTypes from 'prop-types';
import React, { useState } from 'react';
import { getCtgDetail, getStructuredInfo } from '../api/paperApi';



const SearchResults = ({ results, onResultSelect, onViewDetails, originalQuery, refinedQuery, appliedQueries, filters }) => {
  const [isQueryPanelOpen, setIsQueryPanelOpen] = useState(false);
  const [selectedItems, setSelectedItems] = useState([]);
  const [mergeFocus, setMergeFocus] = useState('CTG');

  if (!results) {
    // return (
    //   <div className="mt-6 space-y-10 px-4 w-full max-w-7xl mx-auto">
    //     <div className="bg-white border border-custom-border rounded-xl p-8 text-center">
    //       <p className="text-custom-text-subtle">Enter search terms to find relevant clinical trials and publications.</p>
    //     </div>
    //   </div>
    // );
    return null; // not rendering anything if results are not available
  }

  // Get unified results array and counts with safe fallbacks
  const unifiedResults = Array.isArray(results.results) ? results.results : [];
  const counts = results.counts || { total: 0, merged: 0, pm_only: 0, ctg_only: 0 };

  // Debug logging
  console.log('[SearchResults] Received results:', results);
  console.log('[SearchResults] Unified results type:', typeof unifiedResults);
  console.log('[SearchResults] Unified results length:', unifiedResults.length);
  console.log('[SearchResults] First few items:', unifiedResults.slice(0, 2));
  console.log(refinedQuery, appliedQueries)

  const toggleSelectAll = () => {
    setSelectedItems(selectedItems.length === unifiedResults.length ? [] : [...unifiedResults]);
  };

  const clearSelections = () => {
    setSelectedItems([]);
  };

  const handleDownload = async () => {
    const detailedItems = [];

    for (const item of selectedItems) {
      if(item.type === 'CTG' || item.type === 'MERGED') {
        try {
          const detail = await getCtgDetail({ nctId: item.id || item.nctid }); 
          detailedItems.push(detail.structured_info);
        } catch (err) {
          console.error(`Failed to fetch details for ${item.id}:`, err);
        }
      } else if(item.type === 'PM'){
        try {
          const detail = await getStructuredInfo( { pmcid: item.pmcid, pmid: item.pmid, ref_nctids: item.ref_nctids}); 
          detailedItems.push(detail.structured_info);
        } catch (err) {
          console.error(`Failed to fetch details for ${item.id}:`, err);
        }
      }
    } 

    try {
      const jsonData = JSON.stringify(detailedItems, null, 2); // Pretty-print with 2-space indent
      const blob = new Blob([jsonData], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'cth-results.json';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to create download:', err);
    }
  };
  if (unifiedResults.length === 0) {
    return (
      <div className="mt-6 space-y-10 px-4 w-full max-w-7xl mx-auto">
        <div className="bg-white border border-custom-border rounded-xl p-8 text-center">
          <p className="text-custom-text-subtle">No results found. Try adjusting your search terms or filters.</p>
        </div>
      </div>
    );
  }

  // Toggle focus for merged items (PM or CTG view)
  /* const toggleMergedFocus = (itemId, currentFocus) => {
    setMergedItemFocus(prev => ({
      ...prev,
      [itemId]: currentFocus === 'PM' ? 'CTG' : 'PM'
    }));
  }; */

  // Get display data for merged items based on focus
  const getMergedDisplayData = (item) => {
    const focus = mergeFocus;

    if (focus === 'PM') {
      return {
        focus: 'PM',
        title: item.pm_data?.title || 'No Title Available',
        subtitle: item.pm_data?.journal || '',
        authors: item.pm_data?.authors || [],
        date: item.pm_data?.pubDate || '',
        abstract: item.pm_data?.abstract || '',
        doi: item.pm_data?.doi || '',
        pmcid: item.pm_data?.pmcid || '',
        country: item.pm_data?.country || '',
        // Secondary info from CTG
        secondaryInfo: {
          nctid: item.nctid,
          status: item.ctg_data?.status || '',
          phase: item.ctg_data?.phase || '',
          conditions: item.ctg_data?.conditions || []
        }
      };
    } else {
      return {
        focus: 'CTG',
        title: item.ctg_data?.title || 'No Title Available',
        subtitle: `${item.ctg_data?.phase || 'Unknown Phase'} | ${item.ctg_data?.status || 'Unknown Status'}`,
        conditions: item.ctg_data?.conditions || [],
        summary: item.ctg_data?.brief_summary || '',
        sponsor: item.ctg_data?.lead_sponsor || '',
        outcomes: item.ctg_data?.primary_outcomes || [],
        // Secondary info from PM
        secondaryInfo: {
          pmid: item.pmid,
          journal: item.pm_data?.journal || '',
          authors: item.pm_data?.authors || [],
          pubDate: item.pm_data?.pubDate || ''
        }
      };
    }
  };

  // Enhanced PM metadata rendering - Always show
  const renderEnhancedPMMetadata = (item) => {
    const studyType = item.study_type || 'NA';
    const phase = item.phase || 'NA';
    const designAllocation = item.design_allocation || null;
    const observationalModel = item.observational_model || null;
    const pubYear = item.pub_year || 'NA';
    
    return (
      <div className="text-sm text-custom-text-subtle mb-2">
        <div className="flex items-center gap-4 flex-wrap">
          <span>type: {studyType}</span>
          {/* Phase - Only show for INTERVENTIONAL or if explicitly set */}
          {(studyType === 'INTERVENTIONAL' || (phase && phase !== 'NA')) && (
            <span>phase: {phase}</span>
          )}
          {studyType === 'INTERVENTIONAL' && designAllocation && designAllocation !== 'NA' && (
            <span>design: {designAllocation}</span>
          )}
          {studyType === 'OBSERVATIONAL' && observationalModel && observationalModel !== 'NA' && (
            <span>model: {observationalModel}</span>
          )}
          <span>year: {pubYear}</span>
        </div>
      </div>
    );
  };

  // Enhanced CTG metadata rendering - Always show
  const renderEnhancedCTGMetadata = (item) => {
    const status = item.status || 'NA';
    const phase = item.phase || 'NA';
    const hasResults = typeof item.has_results !== 'undefined' ? (item.has_results ? 'Yes' : 'No') : 'NA';
    const studyType = item.study_type || 'NA';
    const designAllocation = item.design_allocation || null;
    const observationalModel = item.observational_model || null;
    
    return (
      <div className="text-sm text-custom-text-subtle mb-2">
        <div className="flex items-center gap-4 flex-wrap">
          <span>status: {status}</span>
          <span>type: {studyType}</span>
          {/* Phase - Only show for INTERVENTIONAL or if explicitly set */}
          {(studyType === 'INTERVENTIONAL' || (phase && phase !== 'NA')) && (
            <span>phase: {phase}</span>
          )}
          {studyType === 'INTERVENTIONAL' && designAllocation && (
            <span> Design: {designAllocation} </span>
          )}
          {studyType === 'OBSERVATIONAL' && observationalModel && (
            <span> Model: {observationalModel} </span>
          )}
          <span>has result: {hasResults}</span>
        </div>
      </div>
    );
  };

  // Enhanced Merged metadata rendering
  const renderEnhancedMergedMetadata = (item) => {
    const studyType = item.study_type || 'NA';
    const phase = item.phase || 'NA';
    const designAllocation = item.design_allocation || null;
    const observationalModel = item.observational_model || null;
    
    return (
      <div className="text-sm text-custom-text-subtle mb-2">
        <div className="flex items-center gap-4 flex-wrap">
          <span>type: {studyType}</span>
          {/* Phase - Only show for INTERVENTIONAL or if explicitly set */}
          {(studyType === 'INTERVENTIONAL' || (phase && phase !== 'NA')) && (
            <span>phase: {phase}</span>
          )}
          {studyType === 'INTERVENTIONAL' && designAllocation && designAllocation !== 'NA' && (
            <span>design: {designAllocation}</span>
          )}
          {studyType === 'OBSERVATIONAL' && observationalModel && observationalModel !== 'NA' && (
            <span>model: {observationalModel}</span>
          )}
        </div>
      </div>
    );
  };

  const renderResultItem = (item) => {
    const handleTitleClick = async () => {
      if (item.type === 'CTG' || (item.type === 'MERGED')) {
        const detail = await getCtgDetail({ nctId: item.nctid || item.id }); 
        item.study_details = detail.structured_info.protocolSection;
      }
      onResultSelect(item, mergeFocus);
    };

    // Helper function to check if PM data can be viewed in detail
    const canViewPMDetail = (pmItem) => {
      // Check if item has pmcid OR exactly one CTG reference
      const hasPmcid = pmItem.pmcid && pmItem.pmcid.trim();
      const refNctids = pmItem.ref_nctids || [];
      const hasExactlyOneCtgRef = refNctids.length === 1;
      
      return hasPmcid || hasExactlyOneCtgRef;
    };

    // Check if View button should be disabled
    const isViewDisabled = () => {
      if (item.type === 'PM') {
        return !canViewPMDetail(item);
      } else if (item.type === 'MERGED') {
        const focus = mergeFocus || 'PM';
        if (focus === 'PM') {
          return !canViewPMDetail(item.pm_data || {});
        }
      }
      return false; // CTG items are always viewable
    };

    const handleViewDetails = (e) => {
      e.stopPropagation();
      
      // Don't proceed if view is disabled
      if (isViewDisabled()) {
        return;
      }

      // For merged items, we need to decide which view to send to detail page
      if (item.type === 'MERGED') {
        const focus = mergeFocus;
        //mergedItemFocus[item.id] || 'PM';
        const detailItem = {
          ...item,
          source: focus,
          // Include both PM and CTG data for detail page
          pm_data: item.pm_data,
          ctg_data: item.ctg_data,
          // Set primary fields based on focus
          ...(focus === 'PM' ? {
            id: item.pmid,
            pmid: item.pmid,
            pmcid: item.pm_data?.pmcid,
            title: item.pm_data?.title,
            journal: item.pm_data?.journal,
            authors: item.pm_data?.authors,
            pubDate: item.pm_data?.pubDate,
            abstract: item.pm_data?.abstract,
            doi: item.pm_data?.doi
          } : {
            id: item.nctid,
            title: item.ctg_data?.title,
            status: item.ctg_data?.status,
            phase: item.ctg_data?.phase,
            brief_summary: item.ctg_data?.brief_summary,
            lead_sponsor: item.ctg_data?.lead_sponsor,
            conditions: item.ctg_data?.conditions,
            start_date: item.ctg_data?.start_date,
            completion_date: item.ctg_data?.completion_date,
            primary_completion_date: item.ctg_data?.primary_completion_date,
            intervention_names: item.ctg_data?.intervention_names,
            collaborators: item.ctg_data?.collaborators
          })
        };
        onViewDetails(detailItem);
      } else {
        onViewDetails(item);
      }
    };

    // Helper function to format study duration
    const formatStudyDuration = (startDate, completionDate, primaryCompletionDate) => {
      const formatDate = (dateStr) => {
        if (!dateStr) return null;
        try {
          return new Date(dateStr).toLocaleDateString('en-US', { 
            year: 'numeric', 
            month: 'short' 
          });
        } catch {
          return dateStr;
        }
      };

      const start = formatDate(startDate);
      const completion = formatDate(completionDate) || formatDate(primaryCompletionDate);
      
      if (start && completion) {
        return `${start} - ${completion}`;
      } else if (start) {
        return `Started: ${start}`;
      } else if (completion) {
        return `Ends: ${completion}`;
      }
      return null;
    };

    // Render based on item type
    if (mergeFocus === ' ') {
      const displayData = getMergedDisplayData(item);
      const focus = mergeFocus;

      return (
        <li
          key={item.id}
          className="group p-4 bg-white border border-custom-border rounded-2xl shadow-sm hover:shadow-md transition-shadow flex flex-col md:flex-row justify-between gap-4"
        >
          <div className="flex-1 min-w-0">
            {/* Merged item header with focus toggle */}
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={selectedItems.some((i) => i.nctid === item.nctid)}
                  onChange={() =>
                    setSelectedItems((prev) =>
                      prev.some((i) => i.nctid === item.nctid)
                        ? prev.filter((i) => i.nctid !== item.nctid)
                        : [...prev, item]
                    )
                  }
                  className="w-4 h-4 m-1 cursor-pointer rounded border-gray-400"
                />
                <span className="bg-gradient-to-r from-green-400 to-blue-500  text-white text-xs font-semibold px-2 py-1 rounded-full">
                  MERGED
                </span>
                <span
                  //onClick={() => toggleMergedFocus(item.id, focus)}
                  className="flex items-center gap-1 text-xs bg-gray-100 px-2 py-1 rounded-full transition-colors"
                >
                  {focus} View
               
                </span>
              </div>
            </div>

            {/* Title - clickable */}
            <h4 
              onClick={handleTitleClick}
              className="font-semibold group-hover:underline text-base cursor-pointer mb-2 leading-tight"
            >
              {displayData.title}
            </h4>

            {/* Content based on focus */}
            {focus === 'PM' ? (
              <div>
                <div className="text-sm text-custom-text-subtle mb-2">
                  <div className="flex items-center gap-4 flex-wrap">
                    {displayData.date && (
                      <span className="flex items-center gap-1">
                        <Calendar size={14} />
                        {displayData.date}
                      </span>
                    )}
                    {displayData.country && (
                      <span className="flex items-center gap-1">
                        <Earth size={14} />
                        {displayData.country}
                      </span>
                    )}
                    {displayData.subtitle && (
                      <span className="flex items-center gap-1">
                        <Building2 size={14} />
                        {displayData.subtitle}
                      </span>
                    )}
                  </div>
                </div>

                {displayData.authors && displayData.authors.length > 0 && (
                  <p className="text-sm text-custom-text mb-2 flex items-start gap-1">
                    <User size={14} className="mt-0.5 flex-shrink-0" />
                    <span>{displayData.authors.slice(0, 3).join(', ')}{displayData.authors.length > 3 ? ` +${displayData.authors.length - 3} more` : ''}</span>
                  </p>
                )}

                {/* Merged Study metadata */}
                {renderEnhancedMergedMetadata(item)}

                {/* Additional PM metadata for merged items */}
                <div className="space-y-1 text-xs text-custom-text-subtle mb-2">
                  {/* Publication Types */}
                  {item.pm_data?.publication_types && item.pm_data.publication_types.length > 0 && (
                    <div className="flex items-center gap-1 flex-wrap">
                      <span className="font-medium">Types:</span>
                      {item.pm_data.publication_types.slice(0, 3).map((type, idx) => (
                        <span key={idx} className="bg-purple-100 text-purple-800 px-2 py-0.5 rounded-full text-xs">
                          {type}
                        </span>
                      ))}
                      {item.pm_data.publication_types.length > 3 && (
                        <span className="text-custom-text-subtle">+{item.pm_data.publication_types.length - 3} more</span>
                      )}
                    </div>
                  )}
                </div>

                {/* Secondary CTG info */}
                <div className="text-xs text-custom-text-subtle mb-2">
                  <span className="font-medium">Related Clinical Trial:</span>
                  <span className="ml-1">
                    {displayData.secondaryInfo.nctid} | {displayData.secondaryInfo.status}
                  </span>
                  {displayData.secondaryInfo.conditions && displayData.secondaryInfo.conditions.length > 0 && (
                    <span className="ml-1">
                      | {displayData.secondaryInfo.conditions.slice(0, 2).join(', ')}
                    </span>
                  )}
                </div>
              </div>
            ) : (
              <div>
                <div className="text-sm text-custom-text-subtle mb-2">
                  <span className="flex items-center gap-1">
                    {displayData.subtitle}
                  </span>
                </div>

                {/* Study duration and sponsor info for CTG focus */}
                <div className="text-sm text-custom-text mb-2">
                  <div className="flex items-center gap-4 flex-wrap">
                    {/* Study duration */}
                    {(item.ctg_data?.start_date || item.ctg_data?.completion_date || item.ctg_data?.primary_completion_date) && (
                      <span className="flex items-center gap-1">
                        <Clock size={14} />
                        {formatStudyDuration(
                          item.ctg_data.start_date, 
                          item.ctg_data.completion_date, 
                          item.ctg_data.primary_completion_date
                        )}
                      </span>
                    )}
                    
                    {/* Lead sponsor */}
                    {item.ctg_data?.countries && item.ctg_data?.countries.length > 0 && (
                      <span className="flex items-center gap-1">
                        <Earth size={14} />
                        {item.ctg_data.countries.slice(0, 3).join(', ')}
                        {item.ctg_data.countries.length > 3 && ` +${item.ctg_data.countries.length - 3} more`}
                      </span>
                    )}

                    {/* Lead sponsor */}
                    {item.ctg_data?.lead_sponsor && (
                      <span className="flex items-center gap-1">
                        <Building2 size={14} />
                        {item.ctg_data.lead_sponsor}
                      </span>
                    )}
                  </div>
                </div>

                {/* Collaborators */}
                {item.ctg_data?.collaborators && item.ctg_data.collaborators.length > 0 && (
                  <div className="text-xs text-custom-text-subtle mb-2">
                    <span className="font-medium">Collaborators:</span>
                    <span className="ml-1">
                      {item.ctg_data.collaborators.slice(0, 2).join(', ')}
                      {item.ctg_data.collaborators.length > 2 ? ` +${item.ctg_data.collaborators.length - 2} more` : ''}
                    </span>
                  </div>
                )}

                {/* Secondary PM info */}
                <div className="text-xs text-custom-text-subtle mb-2">
                  <span className="font-medium">Related Publication:</span>
                  <span className="ml-1">
                    PMID: {displayData.secondaryInfo.pmid}
                  </span>
                  {displayData.secondaryInfo.journal && (
                    <span className="ml-1">
                      | {displayData.secondaryInfo.journal} | {displayData.secondaryInfo.pubDate}
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* View button */}
          <div className="shrink-0 self-start md:self-center">
            <button
              onClick={handleViewDetails}
              disabled={isViewDisabled()}
              className={`flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-full transition-colors ${
                isViewDisabled()
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : 'bg-primary-100 text-secondary-100 hover:bg-primary-100'
              }`}
            >
              <Eye size={14} /> View
            </button>
          </div>
        </li>
      );

    } else if (item.type === 'PM' || (item.type === 'MERGED' && mergeFocus === 'PM')) {
      const merged = item.type === 'MERGED';
      if (item.type === 'MERGED') item = item.pm_data;
      return (
        <li
          key={item.id}
          className="group p-4 bg-white border border-custom-border rounded-2xl shadow-sm hover:shadow-md transition-shadow flex flex-col md:flex-row justify-between gap-4"
        >
          <div className="flex-1 min-w-0">
            {/* PM item header */}
            <div className="flex items-center gap-2 mb-2">
              <input
                  type="checkbox"
                  checked={selectedItems.some((i) => i.id === item.id)}
                    onChange={() =>
                      setSelectedItems((prev) =>
                        prev.some((i) => i.id === item.id)
                          ? prev.filter((i) => i.id !== item.id)
                          : [...prev, item]
                      )
                    }
                  className="w-4 h-4 m-1 cursor-pointer rounded border-gray-400 "
              />
              { merged && 
              <span className="bg-gradient-to-r from-green-400 to-blue-500  text-white text-xs font-semibold px-2 py-1 rounded-full">
                  MERGED
              </span> }
              <span className="bg-blue-500 text-white text-xs font-semibold px-2 py-1 rounded-full">
                PubMed
              </span>
              {/* Publication types */}
              {item.publication_types && item.publication_types.length > 0 && (
                <div className="space-y-1 text-xs">
                  <div className="flex items-center gap-1 flex-wrap">
                    {item.publication_types.slice(0, 3).map((type, idx) => (
                      <span key={idx} className="flex items-center gap-1 text-xs bg-gray-100 px-2 py-1 rounded-full transition-colors">
                        {type}
                      </span>
                    ))}
                    {item.publication_types.length > 3 && (
                      <span className="text-custom-text-subtle">+{item.publication_types.length - 3} more</span>
                    )}
                  </div>
                </div>
              )}
            </div>
            {/* Title - clickable */}
            <h4 
              onClick={handleTitleClick}
              className="font-semibold group-hover:underline text-base cursor-pointer mb-2 leading-tight"
            >
              {item.title || 'No Title Available'}
            </h4>
            
            {/* Publication metadata */}
            <div className="text-sm text-custom-text mb-2">
              <div className="flex items-center gap-4 flex-wrap">
                {item.pubDate && (
                  <span className="flex items-center gap-1">
                    <Calendar size={14} />
                    {item.pubDate}
                  </span>
                )}
                {item.country && (
                  <span className="flex items-center gap-1">
                    <Earth size={14} />
                    {item.country}
                  </span>
                )}
                {item.journal && (
                  <span className="flex items-center gap-1">
                    <Building2 size={14} />
                    {item.journal}
                  </span>
                )}
              </div>
            </div>

            {/* Authors */}
            {item.authors && item.authors.length > 0 && (
              <p className="text-sm text-custom-text-subtle mb-2 flex items-start gap-1">
                <User size={14} className="mt-0.5 flex-shrink-0" />
                <span>{item.authors.slice(0, 3).join(', ')}{item.authors.length > 3 ? ` +${item.authors.length - 3} more` : ''}</span>
              </p>
            )}

            {/* PM Study metadata - Always show */}
            {renderEnhancedPMMetadata(item)}

            

            {/* IDs section for PM */}
            <div className="text-xs text-custom-text-subtle mt-2">
              <p>
                <a
                  href={`https://pubmed.ncbi.nlm.nih.gov/${item.pmid}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-custom-blue hover:underline"
                  onClick={(e) => e.stopPropagation()}
                >
                  {item.pmid}
                </a>
                {item.pmcid && (
                  <>
                    <span> | </span>
                    <a
                      href={`https://pmc.ncbi.nlm.nih.gov/articles/${item.pmcid}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-custom-blue hover:underline"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {item.pmcid}
                    </a>
                  </>
                )}
                {item.ref_nctids && item.ref_nctids.length > 0 && (
                  <>
                    <span> | </span>
                    {item.ref_nctids.slice(0, 3).map((nctid, idx) => (
                      <React.Fragment key={nctid}>
                        {idx > 0 && <span> | </span>}
                        <a
                          href={`https://clinicaltrials.gov/study/${nctid}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-custom-green hover:underline"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {nctid}
                        </a>
                      </React.Fragment>
                    ))}
                    {item.ref_nctids.length > 3 && (
                      <span className="text-custom-text-subtle"> +{item.ref_nctids.length - 3} more</span>
                    )}
                  </>
                )}
              </p>
            </div>
          </div>

          {/* View button */}
          <div className="shrink-0 self-start md:self-center">
            <button
              onClick={handleViewDetails}
              disabled={isViewDisabled()}
              className={`flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-full transition-colors ${
                isViewDisabled()
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : 'bg-primary-100 text-secondary-100 hover:bg-primary-100'
              }`}
            >
              <Eye size={14} /> View
            </button>
          </div>
        </li>
      );
    } else if (item.type === 'CTG' || (item.type === 'MERGED' && mergeFocus === 'CTG')) {
      const merged = item.type === 'MERGED';
      if (item.type === 'MERGED') item = item.ctg_data;
      return (
        <li
          key={item.id}
          className="group p-4 bg-white border border-custom-border rounded-2xl shadow-sm hover:shadow-md transition-shadow flex flex-col md:flex-row justify-between gap-4"
        >
          <div className="flex-1 min-w-0">
            {/* CTG item header */}
            <div className="flex items-center gap-2 mb-2">
              <input
                  type="checkbox"
                  checked={selectedItems.some((i) => i.id === item.id)}
                    onChange={() =>
                      setSelectedItems((prev) =>
                        prev.some((i) => i.id === item.id)
                          ? prev.filter((i) => i.id !== item.id)
                          : [...prev, item]
                      )
                    }
                  className="w-4 h-4 m-1 cursor-pointer rounded border-gray-400 "
              />
              { merged && 
              <span className="bg-gradient-to-r from-green-400 to-blue-500  text-white text-xs font-semibold px-2 py-1 rounded-full">
                  MERGED
              </span> }
              <span className="bg-green-500 text-white text-xs font-semibold px-2 py-1 rounded-full">
                ClinicalTrials.gov
              </span>
                
              {item.study_type && (
                // if (item.study_type) metas.push(
                <div key="type" className="space-y-1 text-xs flex items-center gap-1 flex-wrap">
                  <span className="flex items-center gap-1 text-xs bg-gray-100 px-2 py-1 rounded-full transition-colors">
                    {item.study_type}
                  </span>
                </div>
              )}
            </div>
            {/* Title - clickable */}
            <h4 
              onClick={handleTitleClick}
              className="font-semibold group-hover:underline text-base cursor-pointer mb-2 leading-tight"
            >
              {item.title || 'No Title Available'}
            </h4>

            {/* Study duration and sponsor info */}
            <div className="text-sm text-custom-text mb-2">
              <div className="flex items-center gap-4 flex-wrap">
                {(item.start_date || item.completion_date || item.primary_completion_date) && (
                  <span className="flex items-center gap-1">
                    <Clock size={14} />
                    {formatStudyDuration(item.start_date, item.completion_date, item.primary_completion_date)}
                  </span>
                )}
                {item.countries && item.countries.length > 0 && (
                  <span className="flex items-center gap-1">
                    <Earth size={14} />
                    {item.countries.slice(0, 3).join(', ')}
                    {item.countries.length > 3 && ` +${item.countries.length - 3} more`}
                  </span>
                )}
                {item.lead_sponsor && (
                  <span className="flex items-center gap-1">
                    <Building2 size={14} />
                    {item.lead_sponsor}
                  </span>
                )}
              </div>
            </div>

            {/* Collaborators */}
            {/* {item.collaborators && item.collaborators.length > 0 && (
              <p className="text-sm text-custom-text-subtle mb-2 flex items-start gap-1">
                <Handshake size={14} className="mt-0.5 flex-shrink-0" />
                <span>{item.collaborators.slice(0, 3).join(', ')}{item.collaborators.length > 3 ? ` +${item.collaborators.length - 3} more` : ''}</span>
              </p>
            )} */}

            {/* Enhanced CTG metadata */}
            {renderEnhancedCTGMetadata(item)}

            {/* IDs section for CTG */}
            <div className="text-xs text-custom-text-subtle mt-2">
              <p>
                <a
                  href={`https://clinicaltrials.gov/study/${item.nctid || item.id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-custom-green hover:underline"
                  onClick={(e) => e.stopPropagation()}
                >
                  {item.nctid || item.id}
                </a>
                {item.pmids && item.pmids.length > 0 && (
                  <>
                    <span> | </span>
                    {item.pmids.slice(0, 3).map((pmid, idx) => (
                      <React.Fragment key={pmid}>
                        {idx > 0 && <span> | </span>}
                        <a
                          href={`https://pubmed.ncbi.nlm.nih.gov/${pmid}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-custom-blue hover:underline"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {pmid}
                        </a>
                      </React.Fragment>
                    ))}
                    {item.pmids.length > 3 && (
                      <span className="text-custom-text-subtle"> +{item.pmids.length - 3} more</span>
                    )}
                  </>
                )}
              </p>
            </div>

          </div>

          {/* View button */}
          <div className="shrink-0 self-start md:self-center">
            <button
              onClick={handleViewDetails}
              disabled={isViewDisabled()}
              className={`flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-full transition-colors ${
                isViewDisabled()
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : 'bg-primary-100 text-secondary-100 hover:bg-primary-100'
              }`}
            >
              <Eye size={14} /> View
            </button>
          </div>
        </li>
      );
    }

    return null;
  };

  return (
    <div className="mt-6 space-y-4 px-4 w-full max-w-7xl mx-auto">
      {(originalQuery || refinedQuery || appliedQueries) && (
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm">
          <button 
            className="w-full px-4 py-3 flex justify-between items-center text-left"
            onClick={() => setIsQueryPanelOpen(!isQueryPanelOpen)}
          >
            <span className="font-medium text-gray-800">Search Results</span>
            <ChevronDown 
              className={`w-5 h-5 text-gray-500 transform transition-transform ${isQueryPanelOpen ? 'rotate-180' : 'rotate-0'}`}
            />
          </button>
          
          {isQueryPanelOpen && (
            <div className="px-4 pb-4 space-y-2 text-sm text-gray-700">
              {appliedQueries?.pubmed && (
                <div>
                  <span className="font-medium">PubMed Search Query: </span>
                  <div className="ml-4 space-y-1">
                    <div>
                      <span className="font-medium">Term: </span>
                      <span className="font-mono text-xs break-all">{appliedQueries.pubmed}</span>
                    </div>
                  </div>
                </div>
              )}
              {appliedQueries?.clinicaltrials && (
                <div>
                  <span className="font-medium">ClinicalTrials.gov Search Query:</span>
                  <div className="ml-4 space-y-1">
                    <div>
                      <span className="font-medium">Term: </span>
                      <span className="font-mono text-xs break-all">{appliedQueries.clinicaltrials}</span>
                    </div>
                    {refinedQuery?.cond && (
                      <div>
                        <span className="font-medium">Condition: </span>
                        <span>{refinedQuery.cond}</span>
                      </div>
                    )}
                    {refinedQuery?.intr && (
                      <div>
                        <span className="font-medium">Intervention: </span>
                        <span>{refinedQuery.intr}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}
              {filters && Object.keys(filters).length && (
                <div className="mt-1">
                  <span className="font-medium text-gray-700 ">Search Filters:</span>
                  {Object.entries({
                    "location": "Location", "city": "City", "state": "State", "country": "Country",
                    "sex": "Gender", "age": "Age", "studyType": "Study Type", "phase": "Phase", "sponsor": "Sponsor"
                  }).filter(([key, value]) => value && filters[key]).map(([key, value]) =>
                    value !== undefined && value !== null && value !== '' ? (
                      <div className="ml-2 space-y-1" key={key}>
                        <span className="font-semibold text-gray-700">{value}:</span>{' '}
                        <span className="text-custom-text">{String(filters[key])}</span>
                      </div>
                    ) : null
                  )}
                </div>
              )}
              {refinedQuery && !appliedQueries.pubmed && !appliedQueries.clinicaltrials && (
                <>
                  <span className="font-medium text-gray-700">ClinicalTrials.gov Search Terms:</span>
                  {Object.entries({
                    "cond": "Condition", "intr": "Intervention", "other_term": "Other Terms", "city": "City", "state": "State", "country": "Country",
                    "sex": "Gender", "age": "Age", "study_type": "Study Type", "phase": "Phase", "sponsor": "Sponsor"
                  }).filter(([key, value]) => value && refinedQuery[key]).map(([key, value]) =>
                    value !== undefined && value !== null && value !== '' ? (
                      <div className="ml-2 space-y-1" key={key}>
                        <span className="font-semibold text-gray-700">{value}:</span>{' '}
                        <span className="text-custom-text">{String(refinedQuery[key])}</span>
                      </div>
                    ) : null
                  )}
                </>
              )}
              
            </div>
          )}
          
          {/* search results statistics */}
          <div className="px-4 py-3 border-t border-gray-200 bg-gray-50 flex flex-wrap justify-start items-center gap-4 text-sm text-gray-600">
            <div>
              <span className="font-medium">Total:</span> {counts.total}
            </div>
            {counts.merged > 0 && (
              <div>
                <span className="font-medium">Merged:</span> {counts.merged}
              </div>
            )}
            {counts.pm_only > 0 && (
              <div>
                <span className="font-medium">PubMed-only:</span> {counts.pm_only}
              </div>
            )}
            {counts.ctg_only > 0 && (
              <div>
                <span className="font-medium">CTG-only:</span> {counts.ctg_only}
              </div>
            )}
          </div>
        </div>
      )}
      <div className="flex justify-between items-center space-x-4 ">
        <div className="flex text-sm items-center ml-1  gap-2">
          <span className="text-custom-text font-semibold">Merged Result View: </span>
          <span className={`font-medium ${mergeFocus === 'PM' ? 'text-blue-700' : 'text-gray-400'}`}>PubMed</span>
          <button
            onClick={() => setMergeFocus(mergeFocus === 'CTG' ? 'PM' : 'CTG')}
            className=" transition-colors"
            aria-label="Toggle merged view"
          >
            {mergeFocus === 'PM' ? (
              <ToggleLeft size={25} strokeWidth={1.5} className=" text-black" />
            ) : (
              <ToggleRight size={25} strokeWidth={1.5} className="text-black" />
            )}
          </button>
          <span className={`font-medium ${mergeFocus === 'CTG' ? 'text-green-500' : 'text-gray-400'}`}>ClinicalTrials.gov</span>
        </div>
        <div className="flex space-x-2">
        <button
          onClick={clearSelections}
          className="px-3 py-1 text-custom-blue-deep justify-end font-semibold border text-sm bg-blue-50 hover:bg-blue-100 rounded-xl"
        >
          Clear Selections ({selectedItems.length})
        </button>
        <button
          onClick={toggleSelectAll}
          className="px-3 py-1 justify-end text-custom-blue-deep font-semibold border text-sm bg-blue-50 hover:bg-blue-100 rounded-xl"
        >
          Select All
        </button>
        <button
          onClick={handleDownload}
          className="px-3 py-1 justify-end text-custom-blue-deep font-semibold border text-sm bg-blue-50 hover:bg-blue-100 rounded-xl"
        >
          Download Selected
        </button>
        </div>
      </div>

      {/* Unified results list */}
      <ul className="space-y-3">
        {unifiedResults.map((item, index) => renderResultItem(item, index))}
      </ul>
    </div>
  );
};

SearchResults.propTypes = {
  results: PropTypes.shape({
    results: PropTypes.arrayOf(PropTypes.object),
    counts: PropTypes.shape({
      total: PropTypes.number,
      merged: PropTypes.number,
      pm_only: PropTypes.number,
      ctg_only: PropTypes.number
    })
  }),
  onResultSelect: PropTypes.func.isRequired,
  onViewDetails: PropTypes.func.isRequired,
  mergedItemFocus: PropTypes.object.isRequired,
  setMergedItemFocus: PropTypes.func.isRequired,
  originalQuery: PropTypes.string,
  refinedQuery: PropTypes.shape({
    cond: PropTypes.string,
    intr: PropTypes.string,
    other_term: PropTypes.string,
    combined_query: PropTypes.string
  }),
  appliedQueries: PropTypes.shape({
    pubmed: PropTypes.string,
    clinicaltrials: PropTypes.string
  }),
  filters: PropTypes.object.isRequired,
};

export default SearchResults;
