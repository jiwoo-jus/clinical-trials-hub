You are provided with structured information about a clinical trial from ClinicalTrials.gov in JSON format.

Structured Information (JSON):
```json
{{structuredInfo}}
```

User Question:
"{{userQuestion}}"

Instructions:
1.  Provide a concise answer based *only* on the provided JSON structured information.
2.  Identify the specific field(s) or value(s) in the JSON that support your answer.
3.  Write your answer in the same language as the user's question. For technical terms found in the JSON, use the original term followed by a parenthetical explanation in the user's language if appropriate.
4.  Maintain a formal tone.
5.  Return your response in JSON format with two keys:
    - `"answer"`: The concise answer.
    - `"evidence"`: An array containing strings that reference the supporting JSON data. This should be the JSON path (e.g., `"protocolSection.eligibilityModule.minimumAge"`). If multiple pieces of evidence support the answer, include them all. If no specific field directly supports the answer but it's inferred, state that in the answer and provide an empty evidence array or a general reference like `"protocolSection"`. Do *not* quote large sections of the JSON.