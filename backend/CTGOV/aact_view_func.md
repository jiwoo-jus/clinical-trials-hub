# View: ctgov_norm
```sql
DROP VIEW IF EXISTS ctgov_norm CASCADE;

CREATE OR REPLACE VIEW ctgov_norm AS
SELECT
  s.nct_id,
  UPPER(TRIM(BOTH FROM s.study_type))          AS study_type_norm,
  UPPER(TRIM(BOTH FROM s.phase))               AS phase_norm,
  s.completion_date,
  EXTRACT(YEAR FROM s.completion_date)::int    AS completion_year,
  UPPER(TRIM(BOTH FROM d.allocation))          AS allocation_norm,
  UPPER(TRIM(BOTH FROM d.observational_model)) AS observational_model_norm,
  e.gender,
  e.minimum_age,
  e.maximum_age,

  /* 최소 나이(년) */
  CASE
    WHEN e.minimum_age IS NULL OR e.minimum_age::text ILIKE 'N/A' THEN NULL::numeric
    WHEN e.minimum_age::text !~* '^[0-9]+(\.[0-9]+)?[[:space:]]*(Year|Month|Week|Day)s?$' THEN NULL::numeric
    ELSE
      (regexp_match(e.minimum_age::text,
                    '([0-9]+(?:\.[0-9]+)?)[[:space:]]*(Year|Month|Week|Day)s?', 'i'))[1]::numeric
      *
      CASE UPPER((regexp_match(e.minimum_age::text,
                               '([0-9]+(?:\.[0-9]+)?)[[:space:]]*(Year|Month|Week|Day)s?', 'i'))[2])
        WHEN 'YEAR'  THEN 1::numeric
        WHEN 'MONTH' THEN 1.0/12::numeric
        WHEN 'WEEK'  THEN 1.0/52::numeric
        WHEN 'DAY'   THEN 1.0/365::numeric
        ELSE NULL::numeric
      END
  END AS min_age_years,

  /* 최대 나이(년) */
  CASE
    WHEN e.maximum_age IS NULL OR e.maximum_age::text ILIKE 'N/A' THEN NULL::numeric
    WHEN e.maximum_age::text !~* '^[0-9]+(\.[0-9]+)?[[:space:]]*(Year|Month|Week|Day)s?$' THEN NULL::numeric
    ELSE
      (regexp_match(e.maximum_age::text,
                    '([0-9]+(?:\.[0-9]+)?)[[:space:]]*(Year|Month|Week|Day)s?', 'i'))[1]::numeric
      *
      CASE UPPER((regexp_match(e.maximum_age::text,
                               '([0-9]+(?:\.[0-9]+)?)[[:space:]]*(Year|Month|Week|Day)s?', 'i'))[2])
        WHEN 'YEAR'  THEN 1::numeric
        WHEN 'MONTH' THEN 1.0/12::numeric
        WHEN 'WEEK'  THEN 1.0/52::numeric
        WHEN 'DAY'   THEN 1.0/365::numeric
        ELSE NULL::numeric
      END
  END AS max_age_years

FROM ctgov.studies s
LEFT JOIN ctgov.designs d       ON d.nct_id = s.nct_id
LEFT JOIN ctgov.eligibilities e ON e.nct_id = s.nct_id;
```

# Function: facets_for_nct_ids
```sql
CREATE OR REPLACE FUNCTION public.facets_for_nct_ids(
  nct_ids text[], 
  start_year integer DEFAULT NULL::integer, 
  end_year integer DEFAULT NULL::integer
)
RETURNS jsonb
LANGUAGE sql
STABLE
AS $function$
WITH seed AS (
  SELECT unnest(nct_ids) AS nct_id
),
base AS (
  SELECT n.*
  FROM ctgov_norm n
  JOIN seed s USING (nct_id)
),
f AS (
  SELECT *
  FROM base
  WHERE (start_year IS NULL OR completion_year >= start_year)
    AND (end_year   IS NULL OR completion_year <= end_year)
),
flagged AS (
  SELECT
    *,
    -- Interventional: determined by study_type only
    (study_type_norm LIKE 'INTERVENTIONAL%')::int AS is_interventional,
    
    -- Observational: determined by study_type OR observational_model presence
    (
      (study_type_norm LIKE 'OBSERVATIONAL%')
      OR (NULLIF(observational_model_norm,'') IS NOT NULL)
    )::int AS is_observational
  FROM f
)
SELECT jsonb_build_object(
  'data_source', jsonb_build_object(
    'pubmed', 0,
    'clinicaltrials_gov', (SELECT COUNT(*) FROM flagged)
  ),
  'publication_date', jsonb_build_object(
    'within_range', jsonb_build_object(
      'start_year', start_year,
      'end_year',   end_year,
      'count',      (SELECT COUNT(*) FROM flagged)
    ),
    'within_1y',  (SELECT COUNT(*) FROM flagged WHERE completion_date >= CURRENT_DATE - INTERVAL '1 year'),
    'within_5y',  (SELECT COUNT(*) FROM flagged WHERE completion_date >= CURRENT_DATE - INTERVAL '5 year'),
    'within_10y', (SELECT COUNT(*) FROM flagged WHERE completion_date >= CURRENT_DATE - INTERVAL '10 year')
  ),
  'article_type', jsonb_build_object(
    'clinical_trial',      (SELECT COUNT(*) FROM flagged WHERE is_interventional=1),
    'observational',       (SELECT COUNT(*) FROM flagged WHERE is_observational=1),
    
    -- Observational studies with Case-only model → Case Report
    'case_report',         (SELECT COUNT(*) FROM flagged
                             WHERE is_observational=1
                               AND observational_model_norm LIKE 'CASE-ONLY%'),
    
    -- Phase (Interventional only; includes multi-phase)
    'phase_i',             (SELECT COUNT(*) FROM flagged
                             WHERE is_interventional=1
                               AND (phase_norm ~ '(^|/)PHASE1(/|$)' OR phase_norm='EARLY_PHASE1')),
    'phase_ii',            (SELECT COUNT(*) FROM flagged
                             WHERE is_interventional=1
                               AND  phase_norm ~ '(^|/)PHASE2(/|$)'),
    'phase_iii',           (SELECT COUNT(*) FROM flagged
                             WHERE is_interventional=1
                               AND  phase_norm ~ '(^|/)PHASE3(/|$)'),
    'phase_iv',            (SELECT COUNT(*) FROM flagged
                             WHERE is_interventional=1
                               AND  phase_norm ~ '(^|/)PHASE4(/|$)'),
    'phase_not_applicable',(SELECT COUNT(*) FROM flagged
                             WHERE is_interventional=1 AND phase_norm='NA'),
    
    'randomized_controlled_trial',
                           (SELECT COUNT(*) FROM flagged
                             WHERE is_interventional=1 AND allocation_norm LIKE 'RANDOMIZED%'),
    
    'meta_analysis',       0,
    'review',              0,
    'systematic_review',   0
  ),
  'additional_filters', jsonb_build_object(
    'species', jsonb_build_object(
      'humans',        NULL,
      'other_animals', NULL
    ),
    'sex', jsonb_build_object(
      'female', (SELECT COUNT(*) FROM flagged WHERE gender = 'Female'),
      'male',   (SELECT COUNT(*) FROM flagged WHERE gender = 'Male')
    ),
    'age', jsonb_build_object(
      'child_0_18',    (SELECT COUNT(*) FROM flagged WHERE min_age_years IS NOT NULL AND min_age_years <= 18),
      'adult_19_plus', (SELECT COUNT(*) FROM flagged WHERE max_age_years IS NOT NULL AND max_age_years >= 19),
      'aged_65_plus',  (SELECT COUNT(*) FROM flagged WHERE max_age_years IS NOT NULL AND max_age_years >= 65)
    )
  )
);
$function$;
```



# Example Queries

```sql
-- All studies with 10 arms
SELECT facets_for_nct_ids(ARRAY(
  SELECT nct_id FROM ctgov.studies WHERE number_of_arms = 10
));

-- Studies with 10 arms completed between 2018 and 2020
SELECT facets_for_nct_ids(
  ARRAY(SELECT nct_id FROM ctgov.studies WHERE number_of_arms = 10),
  2018, 2020
);
```

# Tips

Note: For the case_report aggregation, the function also reads ctgov.designs.observational_model internally to determine whether it is CASE-ONLY. (It is designed to work even if this column is not included in ctgov_norm.)
Records with irregular age parsing formats will have min/max_age_years set to NULL and will be excluded from the corresponding bucket aggregation.

-- Testing queries for study_type and observational_model normalization
-- to support facets_for_nct_ids function

WITH sample AS (
  SELECT nct_id,
         study_type_norm,
         UPPER(TRIM(d.observational_model)) AS observational_model_norm
  FROM ctgov_norm n
  LEFT JOIN ctgov.designs d USING (nct_id)
  LIMIT 1000
)
SELECT
  SUM((study_type_norm LIKE '%INTERVENT%')::int) AS interventional_count,
  SUM(((study_type_norm LIKE '%OBSERV%') OR (observational_model_norm LIKE '%OBSERV%'))::int) AS observational_count
FROM sample;