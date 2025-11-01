import PropTypes from 'prop-types';
import React from 'react';
import { MapPin } from 'lucide-react';
import { 
  VerticalTable, ListField, ShortTextField, PlainTextField,
  ObjectTable, Collapsible, PairsList, transformTextToReadableElements
} from './StructuredInfoFunctions';

const ProtocolSection = ({ data = {} }) => {
  const {
    descriptionModule = {}, identificationModule = {},
    conditionsModule = {}, armsInterventionsModule = {},
    statusModule = {}, designModule = {},
    contactsLocationsModule = {}, eligibilityModule = {},
    referencesModule = {}, outcomesModule = {},
    sponsorCollaboratorsModule = {},
  } = data;

  function formatEnum(enumValue) {
    if (typeof enumValue !== 'string') return '';
    if(enumValue === 'NA') return 'NA'
    return enumValue
      .toLowerCase()
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  }

  const investigatorList =
  Array.isArray(contactsLocationsModule.overallOfficials)
    ? contactsLocationsModule.overallOfficials
        .map(contact => {
          // Format role: remove underscores, lowercase, capitalize each word
          const formattedRole = formatEnum(contact.role)
          return `${formattedRole}: ${contact.name}${contact.affiliation ? `, ${contact.affiliation}` : ''}`;
        })
    : [];

  // Helper for date fields
  const renderDate = (dateStruct) =>
    dateStruct && dateStruct.date ? (
      <span>
        {dateStruct.date}
        {dateStruct.type ? ` (${formatEnum(dateStruct.type)})` : ''}
      </span>
    ) : null;
    
  function referenceList({references, type}){
    return (
      <ul className="list-disc pl-5 ml-1 mb-1">
        {references
          .filter(ref => ref.type === type)
          .map((ref, idx) => (
            
            <li key={idx} className="pl-0 text-custom-text mb-1 text-sm">{ref.citation}<div style={{ height: 2 }} />
              <a target="_blank"
              rel="noopener noreferrer"
              className="hover:underline text-blue-700"
              href={`https://pubmed.ncbi.nlm.nih.gov/${ref.pmid}`}>{`https://pubmed.ncbi.nlm.nih.gov/${ref.pmid}`}</a>
                </li>
          ))}
      </ul>
    )
  }

  // Prepare the two vertical‐tables’ data + presence flags
  const dateData = {
    "Study Start": renderDate(statusModule?.startDateStruct),
    "Primary Completion": renderDate(statusModule?.primaryCompletionDateStruct),
    "Study Completion": renderDate(statusModule?.completionDateStruct)
  };
  const hasDateData = Object.values(dateData).some(v => v);

  const enrolData = {
    "Enrollment": designModule?.enrollmentInfo
      ? `${designModule.enrollmentInfo.count}${designModule.enrollmentInfo.type
          ? ` (${formatEnum(designModule.enrollmentInfo.type)})`
          : ''}`
      : null,
    "Study Type": formatEnum(designModule?.studyType),
    "Phases": Array.isArray(designModule?.phases)
      ? designModule.phases.join(', ')
      : null
  };
  const hasEnrolData = Object.values(enrolData).some(v => v);

  return (
    <div>
      <Collapsible title="Study Overview" defaultOpen>
       <div id="ident" className="flex overflow-x-auto mb-1">
          <div className="flex flex-col gap-y-2 mt-1 mb-2">
          <ShortTextField field = "ClinicalTrials.gov ID" value = {identificationModule?.nctId}/>
          <ShortTextField field = "Sponsor" value = {identificationModule?.organization?.fullName}/>
          </div>
          <div className="flex flex-col gap-y-2 mt-1 mb-2">
          <ShortTextField field = "Other Study ID Numbers" value = {identificationModule?.orgStudyIdInfo?.id}/>
          <ShortTextField field = "Last Update Posted" value = {renderDate(statusModule?.lastUpdatePostDateStruct)}/>
          </div>
       </div>
       <div id = "studyOverview" className = " ">
            <div className = " mb-1">
            <PlainTextField field="Brief Summary" value={descriptionModule?.briefSummary} />
            <PlainTextField field="Detailed Description" value={descriptionModule?.detailedDescription} />
            <PlainTextField field="Official Title" value={identificationModule?.officialTitle} /> 
            <ListField field = "Conditions" value = {conditionsModule?.conditions} />
            <ListField field = "Intervention / Treatment" value = {Array.isArray(armsInterventionsModule?.interventions) ? armsInterventionsModule.interventions.map(iv => iv.name) : []} />
            </div>
            <div className = " items-center flex gap-x-4">
             {(hasDateData || hasEnrolData) && (
               hasDateData && hasEnrolData
                 ? (
                   <div className="flex gap-x-4">
                     <div className="flex-1 mt-1">
                       <VerticalTable data={dateData} />
                     </div>
                     <div className="flex-1">
                       <VerticalTable data={enrolData} />
                     </div>
                   </div>
                 ) : (
                   <div>
                     {hasDateData && <VerticalTable data={dateData} />}
                     {hasEnrolData && <VerticalTable data={enrolData} />}
                   </div>
                 )
             )}
        </div>
        </div>
      </Collapsible>

      <Collapsible title="Contacts and Locations">
        {contactsLocationsModule?.locations && contactsLocationsModule?.locations.length > 0 ? (
          <div>
          <p className="text-sm text-custom-text">This study has {contactsLocationsModule.locations.length} locations.</p>  
          <ul className=" mt-2 space-y-3">
          {contactsLocationsModule.locations.map((loc, i) => (
          <li key={i}>
            <div className="flex items-center font-semibold text-custom-blue-deep text-sm">
               <MapPin className="w-5 h-7 mr-1 text-white fill-blue-200" />
                  {[
                    loc.city,
                    loc.state,
                    loc.country,
                    loc.zip
                  ].filter(Boolean).join(', ')}
                </div>
                {loc.facility && (
                  <div className="text-sm text-gray-500 ml-6">
                    {loc.facility}
                  </div>
                )}
          </li>
          ))}
          </ul>
        </div>
        ) : (
          <div className = "text-sm text-custom-text">No locations listed.</div>
        )}
      </Collapsible>

      <Collapsible title="Participation Requirements"> 
        <PlainTextField field="Eligibility Criteria" value={eligibilityModule?.eligibilityCriteria} />
        <PlainTextField field="Enrollment" value={eligibilityModule?.studyPopulation} />
        <div id="criteria" className="flex overflow-x-auto mt-3">
          <div className="flex flex-col gap-y-2">
          <ShortTextField field = "Eligible Ages" value = {`${eligibilityModule?.minimumAge} to ${eligibilityModule?.maximumAge}`}/>
          <ShortTextField field = "Accepts Healthy Volunteers?" value = {(eligibilityModule?.healthyVolunteers ? "Yes" : "No")}/>
          </div>
          <div className="flex flex-col gap-y-2">
           <ShortTextField field = "Eligible Sexes" value = {formatEnum(eligibilityModule?.sex)}/>
           <ShortTextField field = "Sampling Method" value = {formatEnum(eligibilityModule?.samplingMethod)}/>
          </div>
       </div>
      </Collapsible>

      <Collapsible title=" Study Plan">
        <PairsList title="Design Details" obj = { { "Primary Purpose":formatEnum(designModule?.designInfo?.primaryPurpose),
          "Allocation":formatEnum(designModule?.designInfo?.allocation), "Interventional Model":formatEnum(designModule?.designInfo?.interventionModel),
          "Masking": formatEnum(designModule?.designInfo?.maskingInfo?.masking), "Observational Model": formatEnum(designModule?.designInfo?.observationalModel)
        } }/>
        <ObjectTable
          field="Arm Groups"
          data={
            Array.isArray(armsInterventionsModule?.armGroups)
              ? armsInterventionsModule.armGroups.map(group => ({
                  "Label": `${group.type ? formatEnum(group.type) + ': ' : null}${group.label ?? null}`,
                  "Group Description": group.description ?? null,
                  "Intervention Names": Array.isArray(group.interventionNames) ? group.interventionNames.join(", ") : null,
      
                }))
              : []
          }
        />
        <ObjectTable
          field="Interventions"
          data={
            Array.isArray(armsInterventionsModule?.interventions)
              ? armsInterventionsModule.interventions.map(iv => ({
                  "Name": `${iv.type && iv.name ? formatEnum(iv.type) + ': ' : null}${iv.name ?? null}`,
                  "Description": transformTextToReadableElements(iv.description) ?? null,
                  "Other Names": Array.isArray(iv.otherNames) ? iv.otherNames.join(', ') : null,
                  "Arm Group Labels": Array.isArray(iv.armGroupLabels) ? iv.armGroupLabels.join(', ') : ''
                }))
              : []
          }
        />
        <ObjectTable field="Primary Outcomes" data= {outcomesModule?.primaryOutcomes}/>
        <ObjectTable field="Secondary Outcomes" data= {outcomesModule?.secondaryOutcomes}/>
      </Collapsible>

      <Collapsible title="Collaborators and Investigators">
       <div className = "mt-1"><ShortTextField field="Lead Sponsor" value={sponsorCollaboratorsModule?.leadSponsor?.name} /></div>
       <ListField field = "Investigators" value = {investigatorList} />  
       <ListField field = "Collaborators" value = {Array.isArray(sponsorCollaboratorsModule.collaborators) ? sponsorCollaboratorsModule.collaborators.map(c => c.name) : []} /> 
      </Collapsible>

      <Collapsible title="Publications">
        { referencesModule?.references ? (
          <>
        {Array.isArray(referencesModule.references) && referencesModule.references.filter(ref => ref.type === "RESULT").length > 0 && (
          <>
          <div className="font-medium text-sm text-custom-blue-deep">Study Results</div>
          <div className="border-b border-gray-200 my-1"></div>
           {referenceList({ references: referencesModule.references, type: "RESULT" })}
          </>
        )}
        {Array.isArray(referencesModule.references) && referencesModule.references.filter(ref => ref.type === "DERIVED").length > 0 && (
          <>
          <div className="font-medium text-sm text-custom-blue-deep">From PubMed</div>
          <div className="border-b border-gray-200 my-1"></div>
           {referenceList({ references: referencesModule.references, type: "DERIVED" })}
          </>
        )}
        {Array.isArray(referencesModule.references) && referencesModule.references.filter(ref => ref.type === "BACKGROUND").length > 0 && (
          <>
          <div className="font-medium text-sm text-custom-blue-deep">General</div>
          <div className="border-b border-gray-200 my-1"></div>
           {referenceList({ references: referencesModule.references, type: "BACKGROUND" })}
          </>
        )}
        </>
        ) : (
          <p className = "text-sm text-custom-text">No references available.</p>
        )}
      </Collapsible>

      <Collapsible title="Study Record Dates">
        <div className = " items-center  gap-x-4">
            <div className="font-medium text-sm text-custom-text">Study Registration Dates</div>
            <div className="border-b border-gray-200 my-1"></div>
             <div className="basis-1/3">
              <VerticalTable data= { {"First Submitted":statusModule?.studyFirstSubmitDate, 
                  "First Submitted that Met QC Criteria": statusModule?.studyFirstSubmitQcDate, 
                  "First Posted": renderDate(statusModule?.studyFirstPostDateStruct) } }/>
             </div>
             {statusModule?.resultsFirstSubmitDate ? (
                <>
                  <div className="font-medium text-sm mt-3 text-custom-text">Results Reporting Dates</div>
                  <div className="border-b border-gray-200 my-1"></div>
                  <div className="basis-1/3">
                    <VerticalTable data={{
                      "Results First Submitted": statusModule?.resultsFirstSubmitDate,
                      "Results First Submitted that Met QC Criteria": statusModule?.resultsFirstSubmitQcDate,
                      "Results First Posted": renderDate(statusModule?.resultsFirstPostDateStruct)
                    }} />
                  </div>
                </>
              ) : null} 
              <div className="font-medium text-sm  mt-3 text-custom-text">Study Record Updates</div>
              <div className="border-b border-gray-200 my-1"></div>
              <div className="basis-1/3">
              <VerticalTable data= { {"Last Update Posted": statusModule?.lastUpdateSubmitDate, 
                  "Last Verified": renderDate(statusModule?.lastUpdatePostDateStruct) } }/>
              </div>  
        </div>
      </Collapsible>
    </div>
  );
};

ProtocolSection.propTypes = {
  data: PropTypes.object
};
ProtocolSection.defaultProps = {
  data: {}
};

export default ProtocolSection;