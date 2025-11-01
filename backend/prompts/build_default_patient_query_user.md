The patient query for clinical trial search:

{{patientQuery}}

Extract the following information:

{{promptLines}}

Return a JSON object in the following format, including the requested fields only:

{
    "cond": # the disease or condition mentioned in the input,
    "intr": # the intervention, such as a drug or therapy name,
    "sex": # the biological sex (choose one: "MALE" or "FEMALE") if mentioned,
    "age": # any age groups mentioned,
    "locStr": # any geographic locations (e.g., city or state),
    "city": # extract city from geographic location string, only if given
    "state": # extract state from geographic location string, only if given
    "country": # extract country from geographic location string, only if given
    "phase": # study phase (choose one: "Early Phase 1", "Phase 1", "Phase 2", "Phase 3", or "Phase 4"),
    "study_type": # the type of study (choose one: "Interventional", "Observational" or "Expanded Access"),
    "sponsor": #  the name of the sponsoring organization, if any (classify as one of: "NIH", "Industry", "Other U.S. federal agency" or "All others")
    "other_term":  # any other relevant terms that don't fit in any of the other fields,
    "query": # the user's input query as given
}
