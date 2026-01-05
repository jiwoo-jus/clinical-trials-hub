import PropTypes from 'prop-types';
import React, { useEffect, useMemo, useState } from 'react';
import { PanelLeft, PanelRight, Settings } from 'lucide-react';
import EligibilityCheckResults from './EligibilityCheckResults';
import { checkSystematicReview, getCtgDetail } from '../api/paperApi';

/** ===============================
 *  Config / Utilities
 *  =============================== */
const DEBUG = false;

// Linkify URLs and NCT IDs
const linkify = (text) => {
  if (!text) return text;
  const combinedRegex = /(https?:\/\/[^\s]+)|(NCT\d+)/g;
  const urlPattern = /^https?:\/\//;
  const nctPattern = /^NCT\d+$/;

  const parts = text.split(combinedRegex);

  return parts
    .map((part, index) => {
      if (!part) return null;
      if (urlPattern.test(part)) {
        return (
          <a
            key={`url-${index}`}
            href={part}
            target="_blank"
            rel="noopener noreferrer"
            className="text-custom-blue hover:underline"
          >
            {part}
          </a>
        );
      } else if (nctPattern.test(part)) {
        const nctid = part;
        return (
          <a
            key={`nct-${index}`}
            href={`https://clinicaltrials.gov/study/${nctid}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-custom-green hover:underline"
          >
            {nctid}
          </a>
        );
      } else {
        return part;
      }
    })
    .filter(Boolean);
};

// Extract text content from ClinicalTrials.gov structured info
const extractCtgTextContent = (structuredInfo) => {
  if (!structuredInfo) {
    if (DEBUG) console.log('[extractCtgTextContent] No structured info provided');
    return '';
  }
  const protocol = structuredInfo.protocolSection || structuredInfo;
  const identification = protocol.identificationModule || {};
  const description = protocol.descriptionModule || {};
  const design = protocol.designModule || {};
  const enrollment = protocol.enrollmentModule || design.enrollmentInfo || {};
  const conditions = protocol.conditionsModule || {};
  const interventions = protocol.armsInterventionsModule || {};
  const outcomes = protocol.outcomesModule || {};

  const parts = [];

  if (identification.briefTitle) parts.push(`Title: ${identification.briefTitle}`);
  if (identification.officialTitle) parts.push(`Official Title: ${identification.officialTitle}`);
  if (description.briefSummary) parts.push(`\nBrief Summary:\n${description.briefSummary}`);
  if (description.detailedDescription) parts.push(`\nDetailed Description:\n${description.detailedDescription}`);
  if (design.studyType) parts.push(`\nStudy Type: ${design.studyType}`);
  if (design.phases?.length) parts.push(`Phase: ${design.phases.join(', ')}`);
  if (design.designInfo) {
    const d = design.designInfo;
    if (d.allocation) parts.push(`Allocation: ${d.allocation}`);
    if (d.interventionModel) parts.push(`Intervention Model: ${d.interventionModel}`);
    if (d.primaryPurpose) parts.push(`Primary Purpose: ${d.primaryPurpose}`);
    if (d.maskingInfo?.masking) parts.push(`Masking: ${d.maskingInfo.masking}`);
  }
  const enrollmentCount = enrollment.count || design.enrollmentInfo?.count;
  const enrollmentType = enrollment.type || design.enrollmentInfo?.type;
  if (enrollmentCount) parts.push(`\nEnrollment: ${enrollmentCount}${enrollmentType ? ` (${enrollmentType})` : ''}`);
  if (conditions.conditions?.length) parts.push(`\nConditions: ${conditions.conditions.join(', ')}`);
  if (interventions.interventions?.length) {
    const interventionList = interventions.interventions.map(i => `${i.type}: ${i.name}`).join(', ');
    parts.push(`\nInterventions: ${interventionList}`);
  }
  if (outcomes.primaryOutcomes?.length) {
    const outcomeList = outcomes.primaryOutcomes.slice(0, 3).map((o, i) => `${i + 1}. ${o.measure}`).join('\n');
    parts.push(`\nPrimary Outcomes:\n${outcomeList}`);
  }
  if (conditions.keywords?.length) parts.push(`\nKeywords: ${conditions.keywords.join(', ')}`);

  return parts.join('\n');
};

/** ===============================
 *  Small Presentational Pieces
 *  =============================== */

const Section = ({ title, children, dense }) => (
  <section className="mb-3">
    {title && (
      <h4 className="text-sm font-semibold text-slate-800 mb-2 tracking-tight">
        {title}
      </h4>
    )}
    <div className="rounded-lg p-3 border border-custom-border bg-custom-bg-soft">
      <div className={` ${dense ? 'space-y-2' : 'space-y-2'}`}>{children}</div>
    </div>
  </section>
);
Section.propTypes = {
  title: PropTypes.oneOfType([PropTypes.string, PropTypes.node]),
  children: PropTypes.node,
  dense: PropTypes.bool,
};
Section.defaultProps = { dense: false };

const MetaRow = ({ label, children }) => (
  <div className="flex text-sm leading-6">
    <span className="min-w-[9rem] shrink-0 font-medium text-slate-700">{label}</span>
    <span className="text-slate-800">{children}</span>
  </div>
);
MetaRow.propTypes = {
  label: PropTypes.oneOfType([PropTypes.string, PropTypes.node]).isRequired,
  children: PropTypes.node,
};

const Tag = ({ children }) => (
  <span className="inline-flex items-center text-xs px-2 py-1 rounded-full bg-slate-100 text-slate-700">
    {children}
  </span>
);
Tag.propTypes = { children: PropTypes.node };

const SoftNote = ({ children }) => (
  <div className="mt-2 rounded-md border border-emerald-200 bg-emerald-50 px-2.5 py-1.5">
    <p className="text-xs text-emerald-700">{children}</p>
  </div>
);
SoftNote.propTypes = { children: PropTypes.node };

const CheckItem = ({ option, checked, onToggle }) => (
  <label className="flex items-center justify-between cursor-pointer">
    <div className="flex items-center gap-2">
      <input
        type="checkbox"
        id={option.value}
        checked={checked}
        onChange={() => onToggle(option.value)}
        className="accent-custom-blue w-4 h-4 rounded border-slate-300 focus:ring-2 focus:ring-custom-blue"
      />
      <span className="text-sm text-slate-800">{option.label}</span>
    </div>
  </label>
);
CheckItem.propTypes = {
  option: PropTypes.shape({
    label: PropTypes.oneOfType([PropTypes.string, PropTypes.node]).isRequired,
    value: PropTypes.string.isRequired,
  }).isRequired,
  checked: PropTypes.bool.isRequired,
  onToggle: PropTypes.func.isRequired,
};

/** ===============================
 *  Options
 *  =============================== */

/*const OPTIONS = [
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
  { label: 'Abstract', value: 'ABSTRACT' },
]; */

const PM_OPTIONS = [
  { label: 'Publication Info', value: 'PUBLICATION_INFO' },
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
  { label: 'Secondary Outcomes', value: 'SECONDARY_OUTCOMES' },
];

/** ===============================
 *  Main Component
 *  =============================== */

const DetailSidebar = ({
  selectedResult,
  isVisible = true,
  defaultOpen = false,
  expandedWidth = '30%',
  collapsedWidth = '2rem',
  onToggle,
  otherSidebarOpen = false,
  inclusionCriteria = [],
  exclusionCriteria = [],
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
  ];

  const [isOpen, setIsOpen] = useState(defaultOpen);
  const [settingsOpen, setSettingsOpen] = useState(defaultOpen);
  const [filters, setFilters] = useState(OPTIONS.map(option => option.value));
  const [isMobile, setIsMobile] = useState(false);

  // Eligibility state
  const [eligibilityCheckLoading, setEligibilityCheckLoading] = useState(false);
  const [eligibilityCheckResults, setEligibilityCheckResults] = useState(null);
  const [eligibilityCheckError, setEligibilityCheckError] = useState(null);

  const handleToggleFilter = (value) => {
    setFilters(prev => prev.includes(value) ? prev.filter(v => v !== value) : [...prev, value]);
  };

  useEffect(() => {
    const checkIfMobile = () => setIsMobile(window.innerWidth <= 768);
    checkIfMobile();
    window.addEventListener('resize', checkIfMobile);
    return () => window.removeEventListener('resize', checkIfMobile);
  }, []);

  useEffect(() => {
    if (selectedResult) {
      setIsOpen(true);
      
      // Set appropriate filters based on result type
      if (selectedResult.source === 'PM' || selectedResult.source === 'PMC') {
        // For PM/PMC, use PM options
        setFilters(PM_OPTIONS.map(option => option.value));
      } else if (selectedResult.source === 'CTG') {
        // For CTG, use CTG options
        setFilters(CTG_OPTIONS.map(option => option.value));
      }
    }
  }, [selectedResult]);

  const hasAnyCriteria = useMemo(
    () => inclusionCriteria.length > 0 || exclusionCriteria.length > 0,
    [inclusionCriteria, exclusionCriteria]
  );

  // eligibility checker
  useEffect(() => {
    const hasCriteria = hasAnyCriteria;
    if (!(selectedResult && hasCriteria && isOpen)) {
      setEligibilityCheckResults(null);
      setEligibilityCheckError(null);
      setEligibilityCheckLoading(false);
      return;
    }

    const checkEligibility = async () => {
      try {
        setEligibilityCheckLoading(true);
        setEligibilityCheckError(null);

        let studyId, studyType, textContent;
        let effective = selectedResult;

        if (effective?.type === 'MERGED') {
          if (effective.pm_data) effective = effective.pm_data;
          else if (effective.ctg_data) effective = effective.ctg_data;
        }

        if (effective.source === 'PM' || effective.source === 'PMC') {
          if (!effective.pmcid) {
            setEligibilityCheckLoading(false);
            return;
          }
          studyId = effective.pmcid;
          studyType = 'PMC';
          textContent = null; // backend fetches abstract
        } else if (effective.source === 'CTG') {
          const trialId = effective.nctid || effective.nctId || effective.id;
          if (!trialId) {
            setEligibilityCheckLoading(false);
            return;
          }
          studyId = trialId;
          studyType = 'CTG';

          let structuredInfo = effective.structured_info;
          if (!structuredInfo || Object.keys(structuredInfo).length === 0) {
            try {
              const ctgDetail = await getCtgDetail({ nctId: studyId });
              structuredInfo = ctgDetail.structured_info;
            } catch (fetchError) {
              setEligibilityCheckError('Failed to fetch clinical trial details');
              setEligibilityCheckLoading(false);
              return;
            }
          }
          textContent = extractCtgTextContent(structuredInfo);
          if (!textContent?.trim()) {
            setEligibilityCheckError('No content available for eligibility check');
            setEligibilityCheckLoading(false);
            return;
          }
        } else {
          setEligibilityCheckLoading(false);
          return;
        }

        const requestBody = {
          study_id: studyId,
          study_type: studyType,
          inclusion_criteria: inclusionCriteria,
          exclusion_criteria: exclusionCriteria,
        };
        if (textContent) requestBody.text_content = textContent;

        const results = await checkSystematicReview(requestBody);
        setEligibilityCheckResults(results);
      } catch (error) {
        setEligibilityCheckError(error.message || 'Failed to check eligibility criteria');
      } finally {
        setEligibilityCheckLoading(false);
      }
    };

    checkEligibility();
  }, [selectedResult, inclusionCriteria, exclusionCriteria, isOpen, hasAnyCriteria]);

  // Notify parent
  useEffect(() => {
    if (onToggle) onToggle(isOpen);
  }, [isOpen, onToggle]);

  if (!isVisible) return null;
  if (isMobile && otherSidebarOpen && !isOpen) return null;

  const toggleSidebar = () => {
    setIsOpen(prev => !prev);
    if (settingsOpen) setSettingsOpen(false);
  };
  const toggleSettings = () => {
    setSettingsOpen(prev => !prev);
    if (isOpen) setIsOpen(false);
  };

  /** ---------- Settings UI ---------- */
  const renderSettings = () => {
    const half = Math.ceil(PM_OPTIONS.length / 2);
    const leftColumn = PM_OPTIONS.slice(0, half);
    const rightColumn = PM_OPTIONS.slice(half);

    const halfCTG = Math.ceil(CTG_OPTIONS.length / 2);
    const leftColumnCTG = CTG_OPTIONS.slice(0, halfCTG);
    const rightColumnCTG = CTG_OPTIONS.slice(halfCTG);

    const onToggleFilter = (value) => handleToggleFilter(value);

    return (
      <div className="p-2">
        <Section title="CTG Result Filters" dense>
          <div className="grid grid-cols-2 gap-x-6">
            {[leftColumnCTG, rightColumnCTG].map((column, colIndex) => (
              <div key={colIndex} className="space-y-2">
                {column.map((option) => (
                  <CheckItem
                    key={option.value}
                    option={option}
                    checked={filters.includes(option.value)}
                    onToggle={onToggleFilter}
                  />
                ))}
              </div>
            ))}
          </div>
        </Section>

        <Section title="PM Result Filters" dense>
          <div className="grid grid-cols-2 gap-x-6">
            {[leftColumn, rightColumn].map((column, colIndex) => (
              <div key={colIndex} className="space-y-2">
                {column.map((option) => (
                  <CheckItem
                    key={option.value}
                    option={option}
                    checked={filters.includes(option.value)}
                    onToggle={onToggleFilter}
                  />
                ))}
              </div>
            ))}
          </div>
        </Section>

        <div className="flex justify-end">
          <button
            onClick={toggleSettings}
            className="px-3 py-1 rounded-md bg-custom-blue text-white text-sm font-semibold hover:bg-custom-blue-hover transition"
          >
            Apply Filters
          </button>
        </div>
      </div>
    );
  };

  /** ---------- Eligibility Section ---------- */
  const renderEligibilitySection = () => {
    if (!(inclusionCriteria.length || exclusionCriteria.length)) return null;
    const hasIdentifier = selectedResult && (selectedResult.pmcid || selectedResult.nctid || selectedResult.id);
    if (!hasIdentifier) return null;

    return (
      <Section title="Eligibility Check" dense>
        {eligibilityCheckError ? (
          <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2">
            <p className="text-sm text-rose-700">
              Failed to check eligibility: {eligibilityCheckError}
            </p>
          </div>
        ) : (
          <EligibilityCheckResults
            results={eligibilityCheckResults}
            isLoading={eligibilityCheckLoading}
          />
        )}
      </Section>
    );
  };

  /** ---------- Content (PM/PMC/CTG) ---------- */
  const renderContent = () => {
    if (!selectedResult) {
      return <p className="text-sm text-slate-500">Select a result to view details.</p>;
    }

    // ---- PM or PMC ----
    if (selectedResult.source === 'PM' || selectedResult.source === 'PMC') {
      const pmItem = selectedResult.type === 'MERGED' ? selectedResult.pm_data : selectedResult;
      const abstract = pmItem?.abstract;
      const show = (key) => filters.includes(key);

      return (
        <div>
          {filters.includes('ABSTRACT') && abstract && (
            <Section title="Abstract">
              <div className="space-y-3">
                {Object.entries(abstract).map(([key, value]) => (
                  <div key={key}>
                    <div className="text-[13px] font-medium text-slate-700 mb-1">{key}</div>
                    <div className="text-sm text-slate-800 leading-relaxed">{linkify(value)}</div>
                  </div>
                ))}
              </div>
            </Section>
          )}

          {show('PUBLICATION_INFO') && (
            <Section title="Publication Info" dense>
              <div className="space-y-1">
                {(pmItem?.article_title || pmItem?.title) && (
                  <MetaRow label="Title">
                    {pmItem.article_title || pmItem.title}
                  </MetaRow>
                )}
                {pmItem.journal && <MetaRow label="Journal">{pmItem.journal}</MetaRow>}
                {pmItem.issue && <MetaRow label="Issue">{pmItem.issue}</MetaRow>}
                {pmItem.volume && <MetaRow label="Volume">{pmItem.volume}</MetaRow>}
                {pmItem.authors?.length > 0 && (
                  <MetaRow label="Authors">{pmItem.authors.join(', ')}</MetaRow>
                )}
                {pmItem.pubDate && (
                  <MetaRow label="Published">
                    {new Date(pmItem.pubDate).toLocaleDateString('en-US', {
                      year: 'numeric', month: 'short', day: 'numeric'
                    })}
                  </MetaRow>
                )}
                {pmItem.pmid && (
                  <MetaRow label="PMID">
                    <a
                      href={`https://pubmed.ncbi.nlm.nih.gov/${pmItem.pmid}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-custom-blue hover:underline"
                    >
                      {pmItem.pmid}
                    </a>
                  </MetaRow>
                )}
                {pmItem.pmcid && (
                  <MetaRow label="PMCID">
                    <a
                      href={`https://pmc.ncbi.nlm.nih.gov/articles/${pmItem.pmcid}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-custom-blue hover:underline"
                    >
                      {pmItem.pmcid}
                    </a>
                  </MetaRow>
                )}
                {pmItem.doi && (
                  <MetaRow label="DOI">
                    <a
                      href={`https://doi.org/${pmItem.doi}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-custom-blue hover:underline"
                    >
                      {pmItem.doi}
                    </a>
                  </MetaRow>
                )}
                {pmItem.nctid && (
                  <MetaRow label="Related Trial">
                    <a
                      href={`https://clinicaltrials.gov/study/${pmItem.nctid}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-custom-green hover:underline"
                    >
                      {pmItem.nctid}
                    </a>
                  </MetaRow>
                )}
              </div>
            </Section>
          )}

          {(pmItem.ref_nctids ||
            pmItem.mesh_headings ||
            pmItem.keywords ||
            pmItem.publication_types ||
            pmItem.country) &&
            filters.includes('ADDITIONAL_METADATA') && (
              <Section title="Additional Metadata" dense>
                <div className="space-y-2">
                  {pmItem.ref_nctids?.length > 0 && (
                    <MetaRow label="Related Trials">
                      <div className="flex flex-wrap items-center gap-1">
                        {pmItem.ref_nctids.map((nctid, idx) => (
                          <a
                            key={idx}
                            href={`https://clinicaltrials.gov/study/${nctid}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-custom-green hover:underline text-sm"
                          >
                            {nctid}
                          </a>
                        ))}
                      </div>
                    </MetaRow>
                  )}

                  {pmItem.publication_types?.length > 0 && (
                    <MetaRow label="Types">
                      <div className="flex flex-wrap gap-1">
                        {pmItem.publication_types.map((t, i) => (
                          <Tag key={i}>{t}</Tag>
                        ))}
                      </div>
                    </MetaRow>
                  )}

                  {pmItem.country && <MetaRow label="Country">{pmItem.country}</MetaRow>}

                  {pmItem.mesh_headings?.length > 0 && (
                    <MetaRow label="MeSH">
                      <div className="flex flex-wrap gap-1">
                        {pmItem.mesh_headings.slice(0, 10).map((mesh, i) => (
                          <Tag key={i}>{typeof mesh === 'string' ? mesh : mesh.descriptor || 'Unknown'}</Tag>
                        ))}
                        {pmItem.mesh_headings.length > 10 && (
                          <span className="text-xs text-slate-500">
                            +{pmItem.mesh_headings.length - 10} more
                          </span>
                        )}
                      </div>
                    </MetaRow>
                  )}

                  {pmItem.keywords?.length > 0 && (
                    <MetaRow label="Keywords">
                      <div className="flex flex-wrap gap-1">
                        {pmItem.keywords.slice(0, 8).map((k, i) => <Tag key={i}>{k}</Tag>)}
                        {pmItem.keywords.length > 8 && (
                          <span className="text-xs text-slate-500">
                            +{pmItem.keywords.length - 8} more
                          </span>
                        )}
                      </div>
                    </MetaRow>
                  )}

                  {pmItem.study_type && <MetaRow label="Study Type">{pmItem.study_type}</MetaRow>}
                  {pmItem.design_allocation && (
                    <MetaRow label="Design Allocation">{pmItem.design_allocation}</MetaRow>
                  )}
                  {pmItem.observational_model && (
                    <MetaRow label="Observational Model">{pmItem.observational_model}</MetaRow>
                  )}
                  {pmItem.phase && <MetaRow label="Phase">{pmItem.phase}</MetaRow>}

                  {pmItem.grants?.length > 0 && (
                    <MetaRow label="Grants">
                      <div className="flex flex-wrap gap-1">
                        {pmItem.grants.slice(0, 8).map((g, i) => (
                          <Tag key={i}>
                            {g.agency}, {g.country}
                          </Tag>
                        ))}
                        {pmItem.grants.length > 8 && (
                          <span className="text-xs text-slate-500">
                            +{pmItem.grants.length - 8} more
                          </span>
                        )}
                      </div>
                    </MetaRow>
                  )}
                </div>
              </Section>
            )}
          {renderEligibilitySection()}
        </div>
      );
    }

    // ---- CTG ----
    if (selectedResult.source === 'CTG') {
      const mergedCTG = selectedResult.type === 'MERGED' ? selectedResult.ctg_data : selectedResult;
      const detailedInfo = mergedCTG?.structured_info;
      const hasDetailedInfo = detailedInfo && Object.keys(detailedInfo).length > 0;
      const details = mergedCTG.study_details;

      if (details) {
        mergedCTG.study_details = details;
        mergedCTG.primary_outcomes =
          mergedCTG.study_details.outcomesModule?.primaryOutcomes?.map(o => o.measure);
        mergedCTG.secondary_outcomes =
          mergedCTG.study_details.outcomesModule?.secondaryOutcomes?.map(o => o.measure);
        mergedCTG.groups =
          mergedCTG.study_details.armsInterventionsModule?.armGroups?.map(
            g => `${g.type?.replace('_', ' ')}: ${g.label}`
          );
      }

      const show = (key) => filters.includes(key);

      if (!hasDetailedInfo) {
        return (
          <div className="space-y-1">
            {show('BRIEF_SUMMARY') && mergedCTG.brief_summary && (
              <Section title="Brief Summary" dense>
                <p className="text-sm text-slate-800 leading-relaxed">
                  {linkify(mergedCTG.brief_summary)}
                </p>
              </Section>
            )}

            {show('STUDY_DETAILS') && (
              <Section title="Basic Info" dense>
                <div className="space-y-1">
                  {(mergedCTG?.title || mergedCTG?.brief_title) && (
                    <MetaRow label="Title">{mergedCTG.title || mergedCTG.brief_title}</MetaRow>
                  )}
                  {mergedCTG.countries?.length > 0 && (
                    <MetaRow label="Countries">
                      {mergedCTG.countries.slice(0, 3).join(', ')}
                      {mergedCTG.countries.length > 3 && ` +${mergedCTG.countries.length - 3} more`}
                    </MetaRow>
                  )}
                  {mergedCTG.lead_sponsor && (
                    <MetaRow label="Lead Sponsor">{mergedCTG.lead_sponsor}</MetaRow>
                  )}
                  {(mergedCTG.start_date || mergedCTG.completion_date || mergedCTG.primary_completion_date) && (
                    <MetaRow label="Study Period">
                      {mergedCTG.start_date && new Date(mergedCTG.start_date).toLocaleDateString('en-US', { year: 'numeric', month: 'short' })}
                      {mergedCTG.start_date && (mergedCTG.completion_date || mergedCTG.primary_completion_date) && ' - '}
                      {(mergedCTG.completion_date || mergedCTG.primary_completion_date) && new Date(mergedCTG.completion_date || mergedCTG.primary_completion_date).toLocaleDateString('en-US', { year: 'numeric', month: 'short' })}
                    </MetaRow>
                  )}
                  {mergedCTG.status && <MetaRow label="Status">{mergedCTG.status}</MetaRow>}
                  {mergedCTG.has_results !== undefined && (
                    <MetaRow label="Has Results">
                      <span className="text-sm font-medium text-slate-800">
                        {mergedCTG.has_results ? 'Yes' : 'No'}
                      </span>
                    </MetaRow>
                  )}
                  {(mergedCTG.nctid || mergedCTG.id) && (
                    <MetaRow label="NCTID">
                      <a
                        href={`https://clinicaltrials.gov/study/${mergedCTG.nctid || mergedCTG.id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-custom-green hover:underline"
                      >
                        {mergedCTG.nctid || mergedCTG.id}
                      </a>
                    </MetaRow>
                  )}
                  {mergedCTG.pmids?.length > 0 && (
                    <MetaRow label="Related PMIDs">
                      <div className="flex flex-wrap gap-1">
                        {mergedCTG.pmids.slice(0, 3).map((pmid, idx) => (
                          <a
                            key={idx}
                            href={`https://pubmed.ncbi.nlm.nih.gov/${pmid}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-custom-blue hover:underline text-sm"
                          >
                            {pmid}
                          </a>
                        ))}
                        {mergedCTG.pmids.length > 3 && (
                          <span className="text-xs text-slate-500">+{mergedCTG.pmids.length - 3} more</span>
                        )}
                      </div>
                    </MetaRow>
                  )}
                </div>
              </Section>
            )}

            

            <Section title="Study Design" dense>
              <div className="space-y-1">
                {mergedCTG.study_type && show('STUDY_DETAILS') && (
                  <MetaRow label="Study Type">{mergedCTG.study_type}</MetaRow>
                )}
                {mergedCTG.phase && show('STUDY_DETAILS') && (
                  <MetaRow label="Phase">{mergedCTG.phase}</MetaRow>
                )}
                {mergedCTG.enrollment && (
                  <MetaRow label="Enrollment">
                    {mergedCTG.enrollment}
                    {mergedCTG.enrollment_type && ` (${mergedCTG.enrollment_type})`}
                  </MetaRow>
                )}
                {show('KEYWORDS') && mergedCTG.keywords?.length > 0 && (
                  <MetaRow label="Keywords">
                    <div className="flex flex-wrap gap-1">
                      {mergedCTG.keywords.map((k, i) => <Tag key={i}>{k}</Tag>)}
                    </div>
                  </MetaRow>
                )}
                {show('CONDITIONS') && mergedCTG.conditions?.length > 0 && (
                  <MetaRow label="Conditions">
                    <div className="flex flex-wrap gap-1">
                      {mergedCTG.conditions.map((c, i) => <Tag key={i}>{c}</Tag>)}
                    </div>
                  </MetaRow>
                )}
                {show('INTERVENTIONS') && mergedCTG.intervention_names?.length > 0 && (
                  <MetaRow label="Interventions">
                    <div className="flex flex-wrap gap-1">
                      {mergedCTG.intervention_names.map((intv, i) => <Tag key={i}>{intv}</Tag>)}
                    </div>
                  </MetaRow>
                )}
                {show('ARM_GROUPS') && mergedCTG.groups?.length > 0 && (
                  <MetaRow label="Arm Groups">
                    <div className="flex flex-wrap gap-1">
                      {mergedCTG.groups.map((g, i) => <Tag key={i}>{g}</Tag>)}
                    </div>
                  </MetaRow>
                )}
              </div>
            </Section>

            

            {show('ELIGIBILITY_CRITERIA') && (
              <Section title="Eligibility Criteria" dense>
                <div className="space-y-1">
                  {mergedCTG.study_details?.eligibilityModule?.stdAges && (
                    <MetaRow label="Age Groups">
                      {mergedCTG.study_details.eligibilityModule.stdAges.join(', ').replace('_', ' ')}
                    </MetaRow>
                  )}
                  {mergedCTG.study_details?.eligibilityModule?.sex && (
                    <MetaRow label="Sexes">
                      {mergedCTG.study_details.eligibilityModule.sex}
                    </MetaRow>
                  )}
                  {mergedCTG.study_details?.eligibilityModule?.minimumAge &&
                    mergedCTG.study_details?.eligibilityModule?.maximumAge && (
                      <MetaRow label="Age Range">
                        {mergedCTG.study_details.eligibilityModule.minimumAge} to{' '}
                        {mergedCTG.study_details.eligibilityModule.maximumAge}
                      </MetaRow>
                    )}
                  {'healthyVolunteers' in (mergedCTG.study_details?.eligibilityModule || {}) && (
                    <MetaRow label="Healthy Volunteers">
                      {mergedCTG.study_details.eligibilityModule.healthyVolunteers ? 'Yes' : 'No'}
                    </MetaRow>
                  )}
                </div>
              </Section>
            )}

            {show('PRIMARY_OUTCOMES') && mergedCTG.primary_outcomes?.length > 0 && (
              <Section title="Primary Outcomes" dense>
              
                <ul className="list-disc space-y-1 pl-3">
                  {mergedCTG.primary_outcomes.map((o, i) => (
                    <li key={i} className="text-sm text-slate-800">{o}</li>
                  ))}
                </ul>
                
              </Section>
            )}

            {show('SECONDARY_OUTCOMES') && mergedCTG.secondary_outcomes?.length > 0 && (
              <Section title="Secondary Outcomes" dense>
                <ul className="list-disc space-y-1 pl-3">
                  {mergedCTG.secondary_outcomes.slice(0, 3).map((o, i) => (
                    <li key={i} className="text-sm text-slate-800">{o}</li>
                  ))}
                </ul>
                {mergedCTG.secondary_outcomes.length > 3 && (
                  <p className="text-xs text-slate-500 italic mt-1">
                    +{mergedCTG.secondary_outcomes.length - 3} more secondary outcomes
                  </p>
                )}
              </Section>
            )}

            {(show('COLLABORATORS') || show('INVESTIGATORS')) && (
              <Section title="Additional Metadata" dense>
                <div className="space-y-1">
                  {show('INVESTIGATORS') &&
                    mergedCTG.study_details?.contactsLocationsModule?.overallOfficials?.length > 0 && (
                      <MetaRow label="Investigators">
                        <div className="flex flex-wrap gap-1">
                          {mergedCTG.study_details.contactsLocationsModule.overallOfficials.map((o, i) => (
                            <Tag key={i}>{o.name}, {o.affiliation}</Tag>
                          ))}
                        </div>
                      </MetaRow>
                    )}
                  {show('COLLABORATORS') && mergedCTG.collaborators?.length > 0 && (
                    <MetaRow label="Collaborators">
                      <div className="flex flex-wrap gap-1">
                        {mergedCTG.collaborators.map((c, i) => <Tag key={i}>{c}</Tag>)}
                      </div>
                    </MetaRow>
                  )}
                </div>
              </Section>
            )}

            {renderEligibilitySection()}
          </div>
        );
      }

      // Detailed info
      const d = detailedInfo;
      return (
        <div className="space-y-4">
          
          {/* Study Info */}
          <Section title="Study Info" dense>
            <div>
              {(d.briefTitle || d.officialTitle || mergedCTG?.title || mergedCTG?.brief_title) && (
                <MetaRow label="Title">{d.briefTitle || d.officialTitle || mergedCTG?.title || mergedCTG?.brief_title}</MetaRow>
              )}
              {d.locations?.length > 0 && (
                <MetaRow label="Countries">
                  {Array.from(new Set(d.locations.map(l => l.country))).slice(0, 3).join(', ')}
                  {Array.from(new Set(d.locations.map(l => l.country))).length > 3 && (
                    <> +{Array.from(new Set(d.locations.map(l => l.country))).length - 3} more</>
                  )}
                </MetaRow>
              )}
              {d.leadSponsor && <MetaRow label="Lead Sponsor">{d.leadSponsor}</MetaRow>}
              {(d.startDate || d.completionDate || d.primaryCompletionDate) && (
                <MetaRow label="Study Period">
                  {d.startDate && new Date(d.startDate).toLocaleDateString('en-US', { year: 'numeric', month: 'short' })}
                  {d.startDate && (d.completionDate || d.primaryCompletionDate) && ' - '}
                  {(d.completionDate || d.primaryCompletionDate) && new Date(d.completionDate || d.primaryCompletionDate).toLocaleDateString('en-US', { year: 'numeric', month: 'short' })}
                </MetaRow>
              )}
              {d.overallStatus && <MetaRow label="Status">{d.overallStatus}</MetaRow>}
              {(mergedCTG?.has_results !== undefined || d.hasResults !== undefined) && (
                <MetaRow label="Has Results">
                  <span className="text-sm font-medium text-slate-800">
                    {(mergedCTG?.has_results ?? d.hasResults) ? 'Yes' : 'No'}
                  </span>
                </MetaRow>
              )}
              {(d.nctId || mergedCTG.nctid || mergedCTG.id) && (
                <MetaRow label="NCTID">
                  <a
                    href={`https://clinicaltrials.gov/study/${d.nctId || mergedCTG.nctid || mergedCTG.id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-custom-green hover:underline"
                  >
                    {d.nctId || mergedCTG.nctid || mergedCTG.id}
                  </a>
                </MetaRow>
              )}
              {mergedCTG.pmids?.length > 0 && (
                <MetaRow label="Related PMIDs">
                  <div className="flex flex-wrap gap-1">
                    {mergedCTG.pmids.slice(0, 3).map((pmid, idx) => (
                      <a
                        key={idx}
                        href={`https://pubmed.ncbi.nlm.nih.gov/${pmid}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-custom-blue hover:underline text-sm"
                      >
                        {pmid}
                      </a>
                    ))}
                    {mergedCTG.pmids.length > 3 && (
                      <span className="text-xs text-slate-500">+{mergedCTG.pmids.length - 3} more</span>
                    )}
                  </div>
                </MetaRow>
              )}
            </div>
          </Section>

          {d.briefSummary && (
            <Section title="Brief Summary" dense>
              <p className="text-sm text-slate-800 leading-relaxed">{linkify(d.briefSummary)}</p>
            </Section>
          )}

          {/* Study Design */}
          <Section title="Study Design" dense>
            <div className="space-y-1">
              {d.studyType && <MetaRow label="Study Type">{d.studyType}</MetaRow>}
              {d.phase && <MetaRow label="Phase">{d.phase}</MetaRow>}
              {d.enrollmentCount && (
                <MetaRow label="Enrollment">
                  {d.enrollmentCount}{d.enrollmentType ? ` (${d.enrollmentType})` : ''}
                </MetaRow>
              )}
              {d.keywords?.length > 0 && (
                <MetaRow label="Keywords">
                  <div className="flex flex-wrap gap-1">
                    {d.keywords.map((k, i) => <Tag key={i}>{k}</Tag>)}
                  </div>
                </MetaRow>
              )}
              {d.conditions?.length > 0 && (
                <MetaRow label="Conditions">
                  <div className="flex flex-wrap gap-1">
                    {d.conditions.map((c, i) => <Tag key={i}>{c}</Tag>)}
                  </div>
                </MetaRow>
              )}
              {d.interventions?.length > 0 && (
                <MetaRow label="Interventions">
                  <div className="flex flex-wrap gap-1">
                    {d.interventions.map((intv, i) => <Tag key={i}>{intv.name || intv}</Tag>)}
                  </div>
                </MetaRow>
              )}
              {mergedCTG.study_details?.armsInterventionsModule?.armGroups?.length > 0 && (
                <MetaRow label="Arm Groups">
                  <div className="flex flex-wrap gap-1">
                    {mergedCTG.study_details.armsInterventionsModule.armGroups.map((g, i) => (
                      <Tag key={i}>{`${(g.type || '').replace('_', ' ')}: ${g.label}`}</Tag>
                    ))}
                  </div>
                </MetaRow>
              )}
            </div>
          </Section>

          

          {d.primaryOutcomes?.length > 0 && (
            <Section title="Primary Outcomes" dense>
              <ul className="list-disc space-y-1 pl-3">
                {d.primaryOutcomes.map((o, i) => (
                  <li key={i} className="text-sm text-slate-800">
                    {o.measure}
                    {o.description && (
                      <div className="text-xs text-slate-600 mt-0.5">{linkify(o.description)}</div>
                    )}
                  </li>
                ))}
              </ul>
            </Section>
          )}

          {d.secondaryOutcomes?.length > 0 && (
            <Section title="Secondary Outcomes" dense>
              <ul className="list-disc space-y-1 pl-3">
                {d.secondaryOutcomes.slice(0, 3).map((o, i) => (
                  <li key={i} className="text-sm text-slate-800">
                    {o.measure}
                    {o.description && (
                      <div className="text-xs text-slate-600 mt-0.5">{linkify(o.description)}</div>
                    )}
                  </li>
                ))}
              </ul>
              {d.secondaryOutcomes.length > 3 && (
                <p className="text-xs text-slate-500 italic mt-1">
                  +{d.secondaryOutcomes.length - 3} more secondary outcomes
                </p>
              )}
            </Section>
          )}

          {/* Additional Metadata */}
          {(d.collaborators?.length > 0 || mergedCTG.study_details?.contactsLocationsModule?.overallOfficials?.length > 0) && (
            <Section title="Additional Metadata" dense>
              <div className="space-y-1">
                {mergedCTG.study_details?.contactsLocationsModule?.overallOfficials?.length > 0 && (
                  <MetaRow label="Investigators">
                    <div className="flex flex-wrap gap-1">
                      {mergedCTG.study_details.contactsLocationsModule.overallOfficials.map((o, i) => (
                        <Tag key={i}>{o.name}, {o.affiliation}</Tag>
                      ))}
                    </div>
                  </MetaRow>
                )}
                {d.collaborators?.length > 0 && (
                  <MetaRow label="Collaborators">
                    <div className="flex flex-wrap gap-1">
                      {d.collaborators.map((c, i) => <Tag key={i}>{c}</Tag>)}
                    </div>
                  </MetaRow>
                )}
              </div>
            </Section>
          )}

          <div className="pt-1">
            <a
              href={`https://clinicaltrials.gov/study/${d.nctId || mergedCTG.nctid || mergedCTG.id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-custom-blue hover:underline text-sm font-medium"
            >
              View full study on ClinicalTrials.gov →
            </a>
            <SoftNote>✓ Enhanced details loaded from ClinicalTrials.gov API</SoftNote>
          </div>

          {renderEligibilitySection()}
        </div>
      );
    }

    return <p className="text-sm text-slate-500">Details not available.</p>;
  };

  const getTitle = () => {
    if (!selectedResult || !isOpen) return null;
    if ((selectedResult.source === 'PM' || selectedResult.source === 'PMC') && selectedResult.abstract) {
      return 'PubMed Preview';
    } else if (selectedResult.source === 'CTG') {
      return 'ClinicalTrials.gov Preview';
    }
    return null;
  };

  const title = getTitle();

  return (
    <div
      className={`bg-white shadow-lg border-l border-slate-200 transition-all duration-300 ease-in-out ${
        isOpen ? 'rounded-r-2xl' : 'rounded-l-lg'
      } flex-shrink-0 ${
        isMobile ? (isOpen ? 'fixed right-0 top-0 z-50' : 'fixed right-0 top-16 z-50') : 'sticky top-0'
      }`}
      style={{
        width: isOpen || settingsOpen ? (isMobile ? '100%' : expandedWidth) : collapsedWidth,
        height: isMobile && !isOpen ? 'auto' : isMobile && isOpen ? '100vh' : 'calc(100vh - 64px)'
      }}
    >
      {/* Header */}
      <div className={`flex items-center ${isOpen ? 'justify-between' : 'justify-center'} p-2 border-b border-slate-200`}>
        {isOpen && title && <h3 className="font-semibold text-slate-900 text-base ml-2">{title}</h3>}
        {isOpen && !title && <div />}
        {!settingsOpen && (
          <button
            type="button"
            aria-controls="sidebar-drawer"
            aria-expanded={isOpen}
            className="p-1 text-slate-600 hover:text-slate-900 transition-colors"
            aria-label="Toggle details sidebar"
            onClick={toggleSidebar}
          >
            {isOpen ? <PanelLeft size={18} /> : <PanelRight size={18} />}
          </button>
        )}
      </div>

      {/* Footer / Settings Bar */}
      <div className={`flex items-center ${settingsOpen ? 'justify-between border-b border-slate-200' : 'justify-center'} p-2`}>
        {settingsOpen && <h3 className="font-semibold text-slate-900 text-base ml-2">Study Detail Settings</h3>}
        {settingsOpen && <div />}
        {!isOpen && (
          <button
            className="p-1 text-slate-600 hover:text-slate-900 transition-colors"
            type="button"
            aria-label="Open settings"
            aria-expanded={isOpen}
            onClick={toggleSettings}
          >
            <Settings size={18} />
          </button>
        )}
      </div>

      {/* Body */}
      {isOpen && (
        <div
          className="px-4 py-2 text-sm text-slate-8 00"
          style={{
            height: isMobile ? 'calc(100vh - 41px)' : 'calc(100vh - 64px - 41px)',
            overflowY: 'auto'
          }}
        >
          {renderContent()}
        </div>
      )}

      {/* Settings drawer */}
      {settingsOpen && (
        <div className="px-4 py-2 text-sm text-slate-800" style={{ height: 'calc(100vh - 41px)', overflowY: 'auto' }}>
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
  inclusionCriteria: PropTypes.arrayOf(PropTypes.string),
  exclusionCriteria: PropTypes.arrayOf(PropTypes.string),
};

export default DetailSidebar;
