import React from 'react';
import { formatEnum, MeasurePanel } from './StructuredInfoFunctions';

export function renderBaselinePanels(baselineCharacteristicsModule) {
  if (!baselineCharacteristicsModule) return null;

  // 1. groupMap: group id -> title
  const groupMap = {};
  if (Array.isArray(baselineCharacteristicsModule.groups)) {
    baselineCharacteristicsModule.groups.forEach(group => {
      if (group && group.id) groupMap[group.id] = group.title;
    });
  }

  // 2. participantCountMap: groupId -> value
  const participantCountMap = {};
  if (Array.isArray(baselineCharacteristicsModule.denoms)) {
    baselineCharacteristicsModule.denoms.forEach(denom => {
      if (Array.isArray(denom.counts)) {
        denom.counts.forEach(count => {
          if (count && count.groupId) participantCountMap[count.groupId] = count.value;
        });
      }
    });
  }

   // 3. For each measure, render a panel
  return (Array.isArray(baselineCharacteristicsModule.measures) ? baselineCharacteristicsModule.measures : []).map((measure, idx) => {
    // Gather class and category titles
    const classTitles = [];
    const catTitles = [];
    if (Array.isArray(measure.classes)) {
      measure.classes.forEach(cls => {
        if (cls.title) classTitles.push(cls.title);
        if (Array.isArray(cls.categories)) {
          cls.categories.forEach(cat => {
            if (cat.title) catTitles.push(cat.title);
          });
        }
      });
    }

    // Decide which to use as keys
    let useCategories = true;
    let keys = [];
    if (classTitles.length === 0 && catTitles.length > 0) {
      keys = catTitles;
    } else if (classTitles.length > 0 && catTitles.length === 0) {
      keys = classTitles;
      useCategories = false;
    } else if (catTitles.length > 0) {
      keys = catTitles;
    } else {
      keys = [""];
    }

    // Build measurementMap
    const measurementMap = { _fromCategories: useCategories };
    keys.forEach(key => {
      measurementMap[key] = {};
    });

    // Populate measurementMap
    if (Array.isArray(measure.classes)) {
      if (useCategories) {
        // Use categories as keys
        measure.classes.forEach(cls => {
          if (Array.isArray(cls.categories)) {
            cls.categories.forEach(cat => {
              const key = cat.title || "";
              if (!keys.includes(key)) return;
              if (Array.isArray(cat.measurements)) {
                cat.measurements.forEach(measurement => {
                  const groupId = measurement.groupId;
                  if (!groupId) return;
                  const value = measurement.value ?? "";
                  const spread = measurement.spread ? ` (${measurement.spread})` : measurement.lowerLimit ? ` (${measurement.lowerLimit} to ${measurement.upperLimit})`: '';
                  measurementMap[key][groupId] = `${value}${spread}`;
                });
              }
            });
          }
        });
      } else {
        // Use classes as keys
        measure.classes.forEach(cls => {
          const key = cls.title || "";
          if (!keys.includes(key)) return;
          // If categories exist, use the first category's measurements
          if (Array.isArray(cls.categories) && cls.categories.length > 0) {
            const cat = cls.categories[0];
            if (Array.isArray(cat.measurements)) {
              cat.measurements.forEach(measurement => {
                const groupId = measurement.groupId;
                if (!groupId) return;
                const value = measurement.value ?? "";
                const spread = measurement.spread ? ` (${measurement.spread})` : measurement.lowerLimit ? ` (${measurement.lowerLimit} to ${measurement.upperLimit})`: '';
                measurementMap[key][groupId] = `${value}${spread}`;
              });
            }
          }
        });
      }
    }

    return (
  <MeasurePanel
    key={idx}
    title={measure.title}
    subtitle={`Type: ${formatEnum(measure.paramType)}${measure.dispersionType ? ` (${formatEnum(measure.dispersionType)})` : ""} | Unit: ${measure.unitOfMeasure}`}
  >
    {/* Measurement Table */}
    <table className="w-full table-fixed text-sm border border-gray-300 border-collapse mt-2">
      <thead>
        <tr>
          <th className="px-2 py-1 font-semibold border border-gray-300 text-custom-text bg-blue-50" style={{ width: `${100 / (Object.keys(groupMap).length + 1)}%` }}>
            Arm/Group Title
          </th>
          {Object.keys(groupMap).map(gid => (
            <th
              key={gid}
              className="px-2 py-1 font-semibold border border-gray-300 text-custom-text bg-blue-50"
              style={{ width: `${100 / (Object.keys(groupMap).length + 1)}%` }}
            >
              {groupMap[gid]}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
       
        {Object.keys(measurementMap)
          .filter(key => key !== "_fromCategories")
          .map((key) => (
            <tr key={key}>
              <td className="px-2 py-1 border border-gray-300  bg-gray-50 text-custom-text">{key}</td>
              {Object.keys(groupMap).map(gid => {
                const value = measurementMap[key][gid] ?? "";
                const denom = participantCountMap[gid];
                // If measure.paramType is COUNT_OF_PARTICIPANTS, show value/denom and percent
                if (measure.paramType === "COUNT_OF_PARTICIPANTS" && value && denom && !isNaN(Number(value)) && !isNaN(Number(denom)) && Number(denom) !== 0) {
                  const percent = ((Number(value) / Number(denom)) * 100).toFixed(1);
                    return (
                    <td key={gid} className="px-2 py-1 border border-gray-300 text-custom-text relative">
                      <span>{value}</span>
                      <span
                      className="text-gray-400 text-sm absolute"
                      style={{
                        left: '17%',
                        top: '50%',
                        transform: 'translateY(-50%)'
                      }}
                      >
                      {percent}%
                      </span>
                    </td>
                    );
                }
                return (
                  <td key={gid} className="px-2 py-1 border border-gray-300 text-custom-text">
                    {value}
                  </td>
                );
              })}
            </tr>
        ))}
        {/* Last row: Number of Participants Analyzed */}
        <tr>
          <td className="px-2 py-1 border border-gray-300  text-custom-text bg-gray-50">
            Total Number of Participants Analyzed
          </td>
          {Object.keys(groupMap).map(gid => (
            <td key={gid} className="px-2 py-1 border border-gray-300 text-custom-text">
              {participantCountMap[gid] ?? ""}
            </td>
          ))}
        </tr>
      </tbody>
    </table>
  </MeasurePanel>
);
  });
}

export function renderParticipantFlowPeriods(participantFlowModule) {
  if (!participantFlowModule?.periods || !Array.isArray(participantFlowModule.periods)) return null;

  // 1. Map group id to group title
  const groupMap = {};
  if (Array.isArray(participantFlowModule.groups)) {
    participantFlowModule.groups.forEach(group => {
      if (group && group.id) groupMap[group.id] = group.title;
    });
  }
  const groupIds = Object.keys(groupMap);
  const n = groupIds.length + 1;
  const colWidth = `${100 / n}%`;


  // 2. Build milestoneMap for all periods
  const milestoneMap = {};
  participantFlowModule.periods.forEach(period => {
    const periodMilestones = {};
    if (Array.isArray(period.milestones)) {
      period.milestones.forEach(milestone => {
        const milestoneName = formatEnum(milestone.type);
        periodMilestones[milestoneName] = {};
        if (Array.isArray(milestone.achievements)) {
          milestone.achievements.forEach(ach => {
            if (ach.groupId) {
              periodMilestones[milestoneName][ach.groupId] = ach.numSubjects ?? "";
            }
          });
        }
      });
    }
    milestoneMap[period.title] = periodMilestones;
  });

  // 3. Render tables for each period using milestoneMap
  return (
    <div>
      <table className="w-full table-fixed text-sm border border-gray-300 border-collapse mt-0">
        <thead>
          <tr>
            <th className="px-2 py-1 font-semibold border border-gray-300 text-custom-text bg-blue-50" style={{ width: colWidth }}>
              Arm/Group Title
            </th>
            {groupIds.map(gid => (
              <th
                key={gid}
                className="px-2 py-1 font-semibold border border-gray-300 text-custom-text bg-blue-50"
                style={{ width: colWidth }}
              >
                {groupMap[gid]}
              </th>
            ))}
          </tr>
        </thead>
      </table>
      {Object.entries(milestoneMap).map(([periodTitle, milestones], idx) => (
        <div key={idx} className="">
          {/* Period Title Banner */}
          <div className="w-full bg-neutral-500 text-sm text-white border-r border-l border-gray-300 font-semibold px-2 py-1 mb-0">
            {periodTitle}
          </div>
          {/* Milestone Table */}
          <table className="w-full table-fixed text-sm border border-gray-300 border-collapse mt-0">
            <tbody>
              {Object.entries(milestones).map(([milestoneName, groupData]) => (
                <tr key={milestoneName}>
                  <td className="px-2 py-1 border border-gray-300 bg-gray-50 text-custom-text">{milestoneName}</td>
                  {groupIds.map(gid => (
                    <td key={gid} className="px-2 py-1 border border-gray-300 text-custom-text">
                      {groupData[gid] ?? ""}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}
    
export function renderOutcomeMeasurePanels(outcomeMeasures) {
  if (!Array.isArray(outcomeMeasures)) return null;

  return outcomeMeasures.map((measure, idx) => {
    // 1. Vertical table fields
    const verticalTable = {
      Description: measure.description,
      "Time Frame": measure.timeFrame,
      "Population Description": measure.populationDescription,
      "Units": measure.unitOfMeasure
    };

    // 2. groupMap: group.id -> group.title
    const groupMap = {};
    if (Array.isArray(measure.groups)) {
      measure.groups.forEach(group => {
        if (group && group.id) groupMap[group.id] = group.title;
      });
    }

    // 3. participantCountMap: groupId -> count
    const participantCountMap = {};
    if (Array.isArray(measure.denoms)) {
      measure.denoms.forEach(denom => {
        if (Array.isArray(denom.counts)) {
          denom.counts.forEach(count => {
            if (count && count.groupId) participantCountMap[count.groupId] = count.value;
          });
        }
      });
    }

    // 4. measurementMap
    const measurementMap = {};
    if (Array.isArray(measure.classes)) {
      measure.classes.forEach(cls => {
        const categoryTitle = cls.title || "";
        measurementMap[categoryTitle] = {};
        // Get participant counts for this class if available
        let classParticipantCounts = {};
        if (Array.isArray(cls.denoms)) {
          cls.denoms.forEach(denom => {
            if (Array.isArray(denom.counts)) {
              denom.counts.forEach(count => {
                if (count && count.groupId) classParticipantCounts[count.groupId] = count.value;
              });
            }
          });
        }
        if (Array.isArray(cls.categories)) {
          cls.categories.forEach(category => {
           // const catTitle = category.title || "";
            if (Array.isArray(category.measurements)) {
              category.measurements.forEach(measurement => {
                const groupId = measurement.groupId;
                if (!groupId) return;
                const value = measurement.value ?? "";
                const spread = measurement.spread ? ` (${measurement.spread})` : measurement.lowerLimit ? ` (${measurement.lowerLimit} to ${measurement.upperLimit})`: '';
                         
                // Prefer class-level participant count, else fallback to measure-level
                const participantCount =
                  classParticipantCounts[groupId] ?? participantCountMap[groupId] ?? null;
                if (!measurementMap[categoryTitle][groupId]) {
                  measurementMap[categoryTitle][groupId] = [ `${value}${spread}`, participantCount ];
                }
              });
            }
          });
        }
      });
    }
    const groupIds = Object.keys(groupMap);
    const n = groupIds.length + 1;
    const colWidth = `${100 / n}%`;
    return (
      <MeasurePanel
      key={idx}
      title={measure.title}
      subtitle={`Type: ${formatEnum(measure.type)} | Time Frame: ${measure.timeFrame}`}
      >
      {/* Vertical Table */}
      <table className="mb-2 w-full mt-1 border border-gray-300 text-sm">
        <tbody>
          {Object.entries(verticalTable).map(([key, value]) =>
            value !== undefined && value !== null && value !== '' ? (
              <tr key={key}>
                <td className="px-2 py-1 bg-gray-50 border border-gray-300 text-custom-blue-deep font-semibold whitespace-nowrap align-top">{key}</td>
                <td className=" px-2 py-1 border border-gray-300 text-custom-text">{String(value)}</td>
              </tr>
            ) : null
          )}
        </tbody>
      </table>

      {/* Participant Table */}
      <table className="w-full table-fixed text-sm border border-b-0  border-gray-300 border-collapse mt-2">
        <thead>
        <tr>
          <th style={{ width: colWidth }} className="px-2 py-1 font-semibold border-b-0 border border-gray-300 text-custom-text bg-blue-50">Arm/Group Title</th>
          {groupIds.map(gid => (
          <th key={gid} style={{ width: colWidth }} className="px-2 py-1 font-semibold border-b-0 border border-gray-300 text-custom-text bg-blue-50">{groupMap[gid]}</th>
          ))}
        </tr>
        </thead>
        <tbody>
        <tr>
          <td className="px-2 py-1 bg-gray-50 border border-b-0 border-gray-300 text-custom-text">Overall Number of Participants Analyzed</td>
          {groupIds.map(gid => (
          <td key={gid} className="px-2 py-1 border border-b-0 border-gray-300 text-custom-text">{participantCountMap[gid] ?? ""}</td>
          ))}
        </tr>
        </tbody>
      </table>

      {/* Measurement Tables */}
      {Object.entries(measurementMap).map(([category, groupData], catIdx) => (
        <div key={catIdx}>
        {category !== "" && (
          <div className="w-full bg-neutral-500 text-white border-r border-l border-gray-300 font-semibold px-2 py-1 mb-0">
          {category}
          </div>
        )}
        <table className="w-full table-fixed text-sm border border-gray-300 border-collapse mt-0">
          <thead>
          </thead>
          <tbody>
          {/* Only render this row if any groupData[gid]?.[1] is different from participantCountMap[gid] */}
          {groupIds.some(gid => groupData[gid]?.[1] !== participantCountMap[gid]) && (
            <tr>
            <td className="px-2 py-1 bg-gray-50 border border-gray-300 text-custom-text">Participants Analyzed</td>
            {groupIds.map(gid => (
              <td key={gid} className="px-2 py-1 border border-gray-300 text-custom-text">
              {groupData[gid]?.[1] ?? ""}
              </td>
            ))}
            </tr>
          )}
          <tr>
            <td className="px-2 py-1 bg-gray-50 border border-gray-300 text-custom-text"> Measure Type: {formatEnum(measure.paramType)} {measure.dispersionType ? ` (${measure.dispersionType})` : ""} </td>
            {groupIds.map(gid => (
            <td key={gid} className="px-2 py-1 border border-gray-300 text-custom-text">
              {groupData[gid]?.[0] ?? ""}
            </td>
            ))}
          </tr>
          </tbody>
        </table>
        </div>
      ))}
      </MeasurePanel>
    );
  });
}