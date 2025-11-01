The default query parameters for clinical trial search:

{{inputData}}

Apply the rules below. For each rule, modify only the specified fields, keep others unchanged. Return variations in the required format.

{{queryRules}}

Return query variations in the following format, with the "queries" list containing one object per rule above:

{ "queries": [
  {
    "type": #type of query variation, should follow the guidelines provided in the rule
    "filters": { ... full modified JSON here ... },
    "modified": [...] # a list of all modified fields in the variant query, exactly as they appeared in the original JSON. only include fields that actually had values in input
    "description": #a short statement on the overall scope of the new query (e.g. "Expands location from __ to __", "Focuses intervention to __"). be specific, detailed and concise about what was changed
  },
  ...
] }