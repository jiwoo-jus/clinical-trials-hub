Analyze the following research paper abstract and evaluate each criterion statement for factual truth relative to the abstract.

## Abstract:
{abstract}

## Criteria to Evaluate:
{criteria_list}

## Task (Truth-only Evaluation):
For each criterion statement, determine:
1. **is_true**: true / false / "unclear"
   - Use `true` if the statement is clearly supported (confidence >= 0.6)
   - Use `false` if the statement is clearly contradicted or not supported (confidence >= 0.6)
   - Use `"unclear"` if there's insufficient information (confidence < 0.6)

2. **confidence**: Your confidence level (0.0–1.0)
   - 0.8–1.0: Evidence is explicit and clear
   - 0.6–0.8: Evidence is implied but reasonable
   - < 0.6: Uncertain (must use "unclear")

3. **evidence**: Direct quote from the abstract or "undeterminable"
   - Provide exact quotes when available
   - Use "undeterminable" when the abstract doesn't contain relevant information

4. **reasoning**: Brief explanation of your assessment
   - Explain why you made this determination
   - Note any assumptions or limitations

## Response Format:
Provide your response in JSON format with this exact structure:
```json
{{
   "results": [
      {{
         "id": "inclusion_0",
         "is_true": true/false/"unclear",
         "confidence": 0.85,
         "evidence": "Direct quote from abstract or undeterminable",
         "reasoning": "Brief explanation of the assessment"
      }}
   ]
}}
```

## Important Notes:
- Base assessments ONLY on the abstract content
- Do not make assumptions beyond what's stated or clearly implied
- When uncertain, it's better to mark as "unclear" than to guess

Do NOT apply inclusion/exclusion semantics. Only judge factual truth of each statement relative to the abstract.
