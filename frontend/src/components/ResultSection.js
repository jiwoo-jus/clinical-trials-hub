import React from 'react';
import PropTypes from 'prop-types';
import {
  MeasurePanel,
  ObjectTable,
  Collapsible,
  PlainTextField,
  ShortTextField,
  PairsList
} from './StructuredInfoFunctions';
import {
  renderBaselinePanels,
  renderOutcomeMeasurePanels,
  renderParticipantFlowPeriods
} from './ResultFunctions';

const ResultsSection = ({ data = {} }) => {
  // Ensure data is always an object, even if undefined
  const {
    participantFlowModule = {},
    baselineCharacteristicsModule = {},
    outcomeMeasuresModule = {},
    adverseEventsModule = {},
    moreInfoModule = {}
  } = data;

  // Always guarantee array fields inside modules are arrays
  const outcomeGroups = [];
  const outcomeMeasures = Array.isArray(outcomeMeasuresModule.outcomeMeasures)
    ? outcomeMeasuresModule.outcomeMeasures
    : [];
  outcomeMeasures.forEach(measure => {
    (Array.isArray(measure.groups) ? measure.groups : []).forEach(group => {
      if (!outcomeGroups.some(g => g.id === group.id)) {
        outcomeGroups.push(group);
      }
    });
  });

  const eventGroups = Array.isArray(adverseEventsModule.eventGroups)
    ? adverseEventsModule.eventGroups
    : [];

  function renderEventModule(events) {
    if (eventGroups.length === 0 || !Array.isArray(events)) return null;

    // 1. Map group id to group title
    const groupMap = {};
    adverseEventsModule.eventGroups.forEach(group => {
      if (group && group.id) groupMap[group.id] = group.title;
    });
    const groupIds = Object.keys(groupMap);
    const n = groupIds?.length * 2 + 1; // Each group gets 2 columns (numEvents, %), plus the leftmost term column
    const colWidth = `${100 / n}%`;

    // 2. Build eventMap: { organSystem: { term: { groupId: [numEvents, percentStr] } } }
    let eventMap = {};
    if (Array.isArray(events)) {
      events.forEach(event => {
        const organSys = event.organSystem || "Other";
        if (!eventMap[organSys]) eventMap[organSys] = {};
        const term = event.term || "Unknown";
        if (!eventMap[organSys][term]) eventMap[organSys][term] = {};
        if (Array.isArray(event.stats)) {
          event.stats.forEach(stat => {
            const groupId = stat.groupId;
            if (!groupId) return;
            const numEvents = stat.numEvents ?? "";
            const numAffected = stat.numAffected ?? "";
            const numAtRisk = stat.numAtRisk ?? "";
            let percent = "";
            if (numAffected !== "" && numAtRisk !== "" && Number(numAtRisk) > 0) {
              percent = ((Number(numAffected) / Number(numAtRisk)) * 100).toFixed(1) + "%";
            }
            eventMap[organSys][term][groupId] = [
              numEvents,
              numAffected !== "" && numAtRisk !== "" ? `${numAffected} / ${numAtRisk} (${percent})` : ""
            ];
          });
        }
      });
    }
    const sortedEventMap = {};
    Object.keys(eventMap).sort((a, b) => a.localeCompare(b)).forEach(key => {
      sortedEventMap[key] = eventMap[key];
    });
    eventMap = sortedEventMap;
    // 3. Render tables for each organ system
    return (
      <>
        <table className="w-full table-fixed text-sm border border-gray-300 border-collapse mt-2">
          <tbody>
            <tr>
              <th className="px-2 py-1 font-semibold border border-gray-300 text-custom-text bg-blue-50" style={{ width: colWidth }}>
                Arm/Group Title
              </th>
              {groupIds.map(gid => (
                <th
                  key={gid + "-events"}
                  colSpan={2}
                  className="px-2 py-1 font-semibold border border-gray-300 text-custom-text bg-blue-50 text-center"
                  style={{ width: `calc(${colWidth} * 2)` }}
                >
                  {groupMap[gid]}
                </th>
              ))}
            </tr>
            <tr>
                  <th className="px-2 py-1 border border-gray-300 bg-gray-50" style={{ width: colWidth }}></th>
                  {groupIds.map(gid => (
                    <>
                      <th key={gid + "-numEvents"} className="font-semibold px-2 py-1 border border-gray-300 bg-gray-50 text-center"># Events</th>
                      <th key={gid + "-percent"} className="font-semibold px-2 py-1 border border-gray-300 bg-gray-50 text-center">Affected / At Risk (%)</th>
                    </>
                  ))}
            </tr>
          </tbody>
        </table>
        {Object.entries(eventMap).map(([organSys, terms], idx) => (
          <div key={idx} className="">
            {/* Organ System Banner */}
            <div className="w-full bg-neutral-500 text-sm text-white border-r border-l border-gray-300 font-semibold px-2 py-1 mb-0">
              {organSys}
            </div>
            {/* Event Table */}
            <table className="w-full table-fixed text-sm border border-gray-300 border-collapse mt-0">
              <thead></thead>
              <tbody>
                {Object.entries(terms).map(([term, groupData]) => (
                  <tr key={term}>
                    <td className="px-2 py-1 border border-gray-300 bg-gray-50 text-custom-text">{term}</td>
                    {groupIds.map(gid => (
                      <>
                        <td className="px-2 py-1 border border-gray-300 text-custom-text text-center">
                          {groupData[gid]?.[0] ?? ""}
                        </td>
                        <td className="px-2 py-1 border border-gray-300 text-custom-text text-center">
                          {groupData[gid]?.[1] ?? ""}
                        </td>
                      </>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
      </>
    );
  }
    return (
      <div>
        <Collapsible title="Participant Flow" defaultOpen>
          <PlainTextField field="Pre-Assignment Details" value={participantFlowModule?.preAssignmentDetails}/>
          <PlainTextField field="Recruitment Details" value={participantFlowModule?.recruitmentDetails}/>
          <ObjectTable field="Arm/Group Information" data={Array.isArray(participantFlowModule.groups) ? participantFlowModule.groups : []}/>
          <div className="pt-1 pb-1"><PlainTextField field="Study Periods" value="Discrete stages of a clinical study during which numbers of participants at specific significant events or points of time are reported."/></div>
          {renderParticipantFlowPeriods(participantFlowModule)}
        </Collapsible>

        <Collapsible title="Baseline Characteristics" defaultOpen>
          <p className="text-sm text-custom-text">A description of each baseline or demographic characteristic measured in the clinical study</p>
          <ObjectTable  field="Baseline Groups" data={Array.isArray(baselineCharacteristicsModule.groups) ? baselineCharacteristicsModule.groups : []}/>
          <div className="font-medium text-custom-blue-deep mt-2 text-sm">Baseline Measures</div>
          <div className="border-b border-gray-200 my-1"></div>
          {renderBaselinePanels(baselineCharacteristicsModule)}
        </Collapsible>

        <Collapsible title="Outcome Measures" defaultOpen>
          <p className="text-sm text-custom-text">Data for each primary and secondary outcome measure by arm or comparison group</p>
          <ObjectTable  field="Outcome Groups" data={outcomeGroups}/>
          <div className="font-medium text-custom-blue-deep mt-2 text-sm">Outcome Measures</div>
          <div className="border-b border-gray-200 my-1"></div>
          {renderOutcomeMeasurePanels(outcomeMeasures)}
        </Collapsible>
      
        <Collapsible title="Adverse Events" defaultOpen>
           <p className="text-sm text-custom-text mb-2">Information on any untoward or unfavorable medical occurrence in a participant, including any abnormal sign, symptom, or disease, temporally associated with the participant’s participation in the research</p>
          <PairsList title="Event Reporting Information" obj={{
            "Time Frame": adverseEventsModule?.timeFrame,
            "Description": adverseEventsModule?.description,
            "Frequency Threshold": adverseEventsModule?.frequencyThreshold,
            "All Cause Mortality Comment": adverseEventsModule?.allCauseMortalityComment
          }}/>
          <ObjectTable field="Event Groups" data={Array.isArray(adverseEventsModule?.eventGroups)
          ? adverseEventsModule.eventGroups.map(group => ({
              title: group.title,
              description: group.description
            }))
          : []}/>
        
        {Array.isArray(adverseEventsModule.eventGroups) && adverseEventsModule.eventGroups.length > 0 && (
        <div className="mb-4">
          <div className="font-medium text-custom-blue-deep mt-2 text-sm">All-Cause Mortality</div>
          <div className="border-b border-gray-200 my-1"></div>
          <table className="w-full table-fixed text-sm border border-gray-300 border-collapse mt-2">
          <thead>
            <tr>
            <th className="px-2 py-1 border border-gray-300 bg-blue-50 text-custom-text font-semibold text-center" style={{width: "20%"}}>
              Arm/Group Title
            </th>
            {adverseEventsModule?.eventGroups.map((group) => (
              <th
              key={group.title + "-mortality"}
              className="px-2 py-1 border border-gray-300 bg-blue-50 text-custom-text font-semibold text-center"
              style={{width: `${80 / adverseEventsModule?.eventGroups.length}%`}}
              >
              {group.title}
              </th>
            ))}
            </tr>
          </thead>
          <tbody>
            <tr>
            <td className="px-2 py-1 border border-gray-300 bg-gray-50 text-custom-text">
              Affected / at Risk (%)
            </td>
            {adverseEventsModule?.eventGroups.map((group) => {
              const numAffected = group.deathsNumAffected ?? "";
              const numAtRisk = group.deathsNumAtRisk ?? "";
              let percent = "";
              if (numAffected !== "" && numAtRisk !== "" && Number(numAtRisk) > 0) {
              percent = ((Number(numAffected) / Number(numAtRisk)) * 100).toFixed(1) + "%";
              }
              return (
              <td key={group.title + "-mortality-value"} className="px-2 py-1 border border-gray-300 text-custom-text text-center">
                {numAffected !== "" && numAtRisk !== ""
                ? `${numAffected} / ${numAtRisk} (${percent})`
                : ""}
              </td>
              );
            })}
            </tr>
          </tbody>
          </table>
        </div>
        )}

          {adverseEventsModule?.seriousEvents?.length > 0 &&
            <MeasurePanel
                  title="Serious Events"
                  subtitle={`Total Number of Events: ${adverseEventsModule?.seriousEvents?.length}`}
            >
              {renderEventModule(adverseEventsModule?.seriousEvents)}
            </MeasurePanel>
          }
          {adverseEventsModule?.otherEvents?.length > 0 &&
            <MeasurePanel
                  title="Other Events"
                  subtitle={`Total Number of Events: ${adverseEventsModule?.otherEvents?.length}`}
            >
            {renderEventModule(adverseEventsModule?.otherEvents)}
            </MeasurePanel>
            }
        </Collapsible>

      <Collapsible title="More Information" defaultOpen>
  <div className="flex flex-col space-y-4 mb-2">
    {moreInfoModule?.pointOfContact && (
      <PairsList
        title="Results Point of Contact"
        obj={moreInfoModule.pointOfContact}
      />
    )}

    <div className="text-sm">
      <div className="font-medium text-custom-blue-deep mb-1">
        Certain Agreement Information
      </div>
      <div className="border-b border-gray-200 mb-2"></div>
      <div className="space-y-1">
        <p className="text-sm text-custom-text mb-1">
          {`Principal Investigators ${moreInfoModule?.piSponsorEmployee ? "ARE" : "are NOT"} employed by the organization sponsoring the study.`}
        </p>
        {moreInfoModule?.certainAgreement?.restrictiveAgreement ? (
          <p className="text-sm text-custom-text">
            {`There IS an agreement between Principal Investigators and the Sponsor that restricts the PI's rights to discuss or publish trial results.`}
          </p>
        ) : (
          <p className="text-sm text-custom-text">
            Restrictive agreement information not specified.
          </p>
        )}
      </div>
    </div>
  </div>
  
  <ShortTextField
    field="Limitations / Caveats"
    value={
      moreInfoModule?.limitationsAndCaveats
        ? moreInfoModule.limitationsAndCaveats.description
        : "Not specified"
    }
  />
</Collapsible>
    </div>
    );
}

ResultsSection.propTypes = {
  data: PropTypes.object
};
ResultsSection.defaultProps = {
  data: {}
};

export default ResultsSection