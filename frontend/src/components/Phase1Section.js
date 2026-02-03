import React from 'react';
import PropTypes from 'prop-types';
import { Collapsible, ObjectTable, PairsList, ListField } from './StructuredInfoFunctions';

const Phase1Section = ({ data = {} }) => {
  const {
    regimen_type,
    escalation_type,
    n_drugs,
    drugs,
    dose_levels,
    safety_events,
    warnings
  } = data;

  const renderBool = (value) => (value === true ? 'Y' : '');

  const summary = {
    "Regimen Type": regimen_type,
    "Escalation Type": escalation_type,
    "Number of Drugs": n_drugs
  };

  const drugRows = Array.isArray(drugs)
    ? drugs.map((drug) => ({
        "Drug ID": drug.drug_id,
        "Drug Name": drug.drug_name,
        "Drug Type": drug.drug_type,
        "Escalated": renderBool(drug.is_escalated),
        "Default Schedule": drug.default_schedule
      }))
    : [];

  const doseLevelRows = Array.isArray(dose_levels)
    ? dose_levels.map((level) => ({
        "Level ID": level.level_id,
        "Label": level.level_label,
        "Stratum": level.stratum,
        "Stratum Level": level.stratum_level_number,
        "Patients": level.n_patients,
        "Courses": level.n_courses,
        "MTD": renderBool(level.is_mtd),
        "Drug 1 Dose": level.drug_1_dose,
        "Drug 1 Unit": level.drug_1_dose_unit,
        "Drug 2 Dose": level.drug_2_dose,
        "Drug 2 Unit": level.drug_2_dose_unit,
        "Drug 3 Dose": level.drug_3_dose,
        "Drug 3 Unit": level.drug_3_dose_unit,
        "Drug 4 Dose": level.drug_4_dose,
        "Drug 4 Unit": level.drug_4_dose_unit
      }))
    : [];

  const safetyEventRows = Array.isArray(safety_events)
    ? safety_events.map((event) => ({
        "Event ID": event.event_id,
        "Dose Level": event.level_id,
        "Toxicity": event.toxicity_term,
        "Grade": event.toxicity_grade,
        "Patients": event.toxicity_patients,
        "Courses": event.toxicity_courses,
        "DLT": renderBool(event.is_dlt),
        "Evidence": Array.isArray(event.evidence_spans)
          ? event.evidence_spans.join(" | ")
          : event.evidence_spans
      }))
    : [];

  const hasSummary = Object.values(summary).some((value) => value !== null && value !== undefined && value !== '');
  const hasDrugs = drugRows.length > 0;
  const hasDoseLevels = doseLevelRows.length > 0;
  const hasSafetyEvents = safetyEventRows.length > 0;
  const hasWarnings = Array.isArray(warnings) && warnings.length > 0;

  if (!hasSummary && !hasDrugs && !hasDoseLevels && !hasSafetyEvents && !hasWarnings) {
    return <div className="text-custom-text-subtle text-sm">No Phase I toxicity data available.</div>;
  }

  return (
    <div>
      {hasSummary && (
        <Collapsible title="Regimen Summary" defaultOpen>
          <PairsList title="Summary" obj={summary} />
        </Collapsible>
      )}

      {hasDrugs && (
        <Collapsible title="Drugs" defaultOpen>
          <ObjectTable field="Drugs" data={drugRows} />
        </Collapsible>
      )}

      {hasDoseLevels && (
        <Collapsible title="Dose Levels" defaultOpen>
          <ObjectTable field="Dose Levels" data={doseLevelRows} />
        </Collapsible>
      )}

      {hasSafetyEvents && (
        <Collapsible title="Safety Events" defaultOpen>
          <ObjectTable field="Safety Events" data={safetyEventRows} />
        </Collapsible>
      )}

      {hasWarnings && (
        <Collapsible title="Warnings" defaultOpen>
          <ListField field="Warnings" value={warnings} />
        </Collapsible>
      )}
    </div>
  );
};

Phase1Section.propTypes = {
  data: PropTypes.object
};

Phase1Section.defaultProps = {
  data: {}
};

export default Phase1Section;
