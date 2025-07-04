# CONTEXT #
You are tasked with analyzing clinical trial study reports or papers to extract specific information as structured data. Omit any fields if the corresponding data does not exist in the target articles. Do not invent or assume information that is not present in the given content.
# PAPER CONTENT #
{{paperContent}}
# TARGET #
- Extract the identificationModule of the study. It includes identifying information such as the trial’s unique identifier or title, illustrating “who is conducting which trial and where it is registered."
- Extract the descriptionModule of the study. It offers a brief introduction or summary of the clinical trial.
- Extract the conditionsModule of the study. It specifies the target conditions or topics (keywords), indicating which are being studied.
- Extract the designModule of the study. It defines the overall study design (study type, phase, allocation, masking, number of participants, etc.) in detail.
- Extract the armsInterventionsModule of the study. It details which drugs (or procedures) are administered, to which arms (groups), and how they are applied.
- Extract the outcomesModule of the study. It dsscribes the primary, secondary, and other outcome measures, showing which indicators are used to assess the trial’s effectiveness and safety.
- Extract the eligibilityModule of the study. It specifies the eligibility criteria for participating in this clinical trial.
# RESPONSE #
The JSON response must adhere to the following structure, where each field is annotated with its expected type.
Ensure that the output is a valid and correctly formatted JSON string.
Format:
```json
"protocolSection": {{
    "identificationModule": {{
        "nctId": \\ ClinicalTrials.gov Identifier. The format is "NCT" followed by an 8-digit number: TEXT (max 11 chars)
        "orgStudyIdInfo": {{
            "id": \\ organization's unique protocol ID: TEXT (max 30 chars)
            "type": \\ Type of organization-issued ID: ENUM (NIH, FDA, VA, CDC, AHRQ, SAMHSA)
            "link": \\ URL link related to OrgStudyId and OrgStudyIdType: TEXT
        }},
        "secondaryIdInfos": [ \\ ARRAY of OBJECT
            {{
                "id": \\ Secondary identifier for funding or registry: TEXT (max 30 chars)
                "type": \\ Type of secondary ID: ENUM (NIH, FDA, VA, CDC, AHRQ, SAMHSA, OTHER_GRANT, EUDRACT_NUMBER, CTIS, REGISTRY, OTHER)
                "domain": \\ Name of funding organization, registry, or issuer: TEXT (max 119 chars)
                "link": \\ URL link related to SecondaryId and SecondaryIdType: TEXT
            }}
        ],
        "organization": {{
            "fullName": \\ Name of the sponsoring organization: TEXT
            "class": \\ Organization type: ENUM (NIH, FED, OTHER_GOV, INDIV, INDUSTRY, NETWORK, AMBIG, OTHER, UNKNOWN)
        }},
        "briefTitle": \\ Short title of the study: TEXT (max 300 chars)
        "officialTitle": \\ Full official title of the study: TEXT (max 600 chars)
        "acronym": \\ Study acronym: TEXT (max 14 chars)
    }},
    "descriptionModule": {{
        "briefSummary": \\ Concise summary of the study, including its hypothesis, in layman's terms: TEXT (max 5000 chars)
        "detailedDescription": \\ Extended study description with technical details, excluding full protocol or duplicate information: TEXT (max 32000 chars)
    }},
    "conditionsModule": {{
        "conditions": \\ List of disease(s) or condition(s) studied, preferably using MeSH or SNOMED CT terms: ARRAY of TEXT
        "keywords": \\ List of descriptive words or phrases related to the study, preferably using MeSH terms: ARRAY of TEXT
    }},
    "designModule": {{
        "studyType": \\ Study classification: ENUM (EXPANDED_ACCESS, INTERVENTIONAL, OBSERVATIONAL)
        "patientRegistry": \\ Indicates if the study is a patient registry: BOOLEAN
        "targetDuration": \\ Follow-up duration for observational patient registry studies: TIME
        "phases": \\ Study phase(s), applicable for drug/biologic trials: ARRAY of ENUM (NA, EARLY_PHASE1, PHASE1, PHASE2, PHASE3, PHASE4)
        "designInfo": {{
            "allocation": \\ Method of assigning participants: ENUM (RANDOMIZED, NON_RANDOMIZED, NA)
            "interventionModel": \\ Type of intervention design: ENUM (SINGLE_GROUP, PARALLEL, CROSSOVER, FACTORIAL, SEQUENTIAL)
            "interventionModelDescription": \\ Description of the intervention model: TEXT
            "primaryPurpose": \\ The main objective of the intervention(s) being evaluated by the clinical trial: ENUM (TREATMENT, PREVENTION, DIAGNOSTIC, ECT, SUPPORTIVE_CARE, SCREENING, HEALTH_SERVICES_RESEARCH, BASIC_SCIENCE, DEVICE_FEASIBILITY, OTHER)
            "observationalModel": \\ Study model for observational studies: ENUM (COHORT, CASE_CONTROL, CASE_ONLY, CASE_CROSSOVER, ECOLOGIC_OR_COMMUNITY, FAMILY_BASED, DEFINED_POPULATION, NATURAL_HISTORY, OTHER)
            "timePerspective": \\ Time perspective for observational studies: ENUM (RETROSPECTIVE, PROSPECTIVE, CROSS_SECTIONAL, OTHER)
            "maskingInfo": {{
                "masking": \\ Level of blinding: ENUM (NONE, SINGLE, DOUBLE, TRIPLE, QUADRUPLE)
                "maskingDescription": \\ Detailed description of masking: TEXT (max 1000 chars)
                "whoMasked": \\ Groups involved in masking: ARRAY of ENUM (PARTICIPANT, CARE_PROVIDER, INVESTIGATOR, OUTCOMES_ASSESSOR)
            }}
        }},
        "enrollmentInfo": {{
            "count": \\ Number of participants enrolled: NUMERIC
            "type": \\ Actual or estimated enrollment: ENUM (ACTUAL, ESTIMATED)
        }}
    }},
    "armsInterventionsModule": {{
        "armGroups": [ \\ ARRAY of OBJECT
            {{
                "label": \\ Name of the arm/group: TEXT
                "type": \\ Type of arm: ENUM (EXPERIMENTAL, ACTIVE_COMPARATOR, PLACEBO_COMPARATOR, SHAM_COMPARATOR, NO_INTERVENTION, OTHER)
                "description": \\ Description of the arm/group: TEXT
                "interventionNames": \\ List of interventions used in this arm/group: ARRAY of TEXT
            }}
        ],
        "interventions": [ \\ ARRAY of OBJECT
            {{
                "type": \\ Type of intervention: ENUM (BEHAVIORAL, BIOLOGICAL, COMBINATION_PRODUCT, DEVICE, DIAGNOSTIC_TEST, DIETARY_SUPPLEMENT, DRUG, GENETIC, PROCEDURE, RADIATION, OTHER)
                "name": \\ Name of the intervention: TEXT
                "description": \\ Description of the intervention: TEXT
                "armGroupLabels": \\ List of arm/group labels associated with this intervention: ARRAY of TEXT
            }}
        ]
    }},
    "outcomesModule": {{
        "primaryOutcomes": [ \\ Required. List of primary outcome measures used to assess the trial's main objectives: ARRAY of OBJECT
            {{
                "measure": \\ Name of the primary outcome measure: TEXT (max 255 chars)
                "description": \\ Description of the metric used to characterize the primary outcome measure: TEXT (max 999 chars)
                "timeFrame": \\ Time point(s) at which the outcome is measured: TEXT (max 255 chars)
            }}
        ],
        "secondaryOutcomes": [ \\ Conditional. List of secondary outcome measures for additional study assessments: ARRAY of OBJECT
            {{
                "measure": \\ Name of the secondary outcome measure: TEXT
                "description": \\ Description of the metric used to characterize the secondary outcome measure: TEXT
                "timeFrame": \\ Time point(s) at which the outcome is measured: TEXT
            }}
        ],
        "otherOutcomes": [ \\ Optional. List of other pre-specified outcome measures (excluding post-hoc measures): ARRAY of OBJECT
            {{
                "measure": \\ Name of the pre-specified outcome measure: TEXT
                "description": \\ Description of the metric used to characterize the outcome measure: TEXT
                "timeFrame": \\ Time point(s) at which the outcome is measured: TEXT
            }}
        ]
    }},
    "eligibilityModule": {{
        "eligibilityCriteria": \\ Inclusion and exclusion criteria for participant selection, formatted as a bulleted list under respective headers: TEXT (max 20000 chars)
        "healthyVolunteers": \\ Indicates if healthy volunteers without the studied condition can participate: BOOLEAN
        "sex": \\ Eligible participant sex: ENUM (FEMALE, MALE, ALL)
        "minimumAge": \\ Minimum age required for participation, with unit of time: TEXT (Years, Months, Weeks, Days, Hours, Minutes, N/A)
        "maximumAge": \\ Maximum age allowed for participation, with unit of time: TEXT (Years, Months, Weeks, Days, Hours, Minutes, N/A)
        "stdAges": \\ Standardized age categories: ARRAY of ENUM (CHILD, ADULT, OLDER_ADULT)
        "studyPopulation": \\ (Observational studies only) Description of the population source for cohorts or groups: TEXT (max 1000 chars)
        "samplingMethod": \\ (Observational studies only) Method used for sampling: ENUM (PROBABILITY_SAMPLE, NON_PROBABILITY_SAMPLE)
    }}
}}
```