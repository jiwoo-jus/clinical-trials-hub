"""
Query Refinement Service

Responsible for improving user search queries.
"""

import os
import json
from typing import Dict
import openai
from pathlib import Path


class QueryService:
    """Query refinement service using LiteLLM"""
    
    def __init__(self):
        # Check environment variables
        self.api_key = os.getenv("LITELLM_API_KEY")
        self.base_url = os.getenv("LITELLM_BASE_URL")
        
        self.client = None
        
        # Validate environment variables
        missing_vars = []
        if not self.api_key:
            missing_vars.append("LITELLM_API_KEY")
        if not self.base_url:
            missing_vars.append("LITELLM_BASE_URL")
            
        if missing_vars:
            print(f"⚠️  Warning: LiteLLM environment variables not set: {', '.join(missing_vars)}")
            print("   Query refinement feature will be disabled.")
            return
        
        # Initialize client
        try:
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            print("✅ LiteLLM query refinement client initialized")
        except Exception as e:
            print(f"⚠️  Warning: Failed to initialize LiteLLM query refinement client: {e}")
            self.client = None
    
    def load_prompt(self, file_name: str, variables: dict) -> str:
        """Load prompt template and substitute variables"""
        # Path from services to prompts directory
        prompt_path = Path(__file__).parent.parent / "prompts" / file_name
        
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                template = f.read()
        except Exception as e:
            raise Exception(f"Error reading prompt file ({prompt_path}): {e}")
        
        # Substitute variables
        for key, value in variables.items():
            template = template.replace(f"{{{{{key}}}}}", str(value))
        
        return template
    
    def refine_query(self, input_data: dict) -> dict:
        """Refine query"""
        if not self.client:
            return {"error": "LiteLLM client not initialized"}
            
        print("[QueryService] Refining query")
        
        try:
            prompt_system = self.load_prompt("refine_query_prompt_system.md", {})
            prompt_user = self.load_prompt("refine_query_prompt_user.md", {
                "inputData": json.dumps(input_data, ensure_ascii=False, indent=2)
            })
            
            response = self.client.chat.completions.create(
                model="GPT-4o",
                messages=[
                    {"role": "system", "content": prompt_system},
                    {"role": "user", "content": prompt_user}
                ],
                response_format={"type": "json_object"},
                temperature=0
            )
            
            refined_query = response.choices[0].message.content.strip()
            try:
                parsed = json.loads(refined_query)
                # Clean None values
                for key in ['cond', 'intr', 'other_term']:
                    if parsed.get(key) in ['None', '', None]:
                        parsed[key] = None
                return parsed
            except Exception as e:
                raise Exception("Failed to parse Refined Query response") from e
            
        except Exception as e:
            print(f"[QueryService] Query refinement error: {e}")
            return {"error": f"Query refinement failed: {e}"}

    def build_patient_default(self, input_data: dict) -> dict:
        if not input_data.get("user_query"):
            return input_data
        
        field_descriptions = {
            "cond": "Extract the disease or condition mentioned in the input.",
            "intr": "Extract the intervention, such as a drug or therapy name.",
            "sex": "Determine the biological sex (MALE or FEMALE) if mentioned.",
            "age": "Extract all age groups (child, adult or older) mentioned.",
            "locStr": "Extract any geographic locations (e.g., city or state) mentioned.",
            "city": "extract city (e.g. Toronto, Columbus) from geographic location string",
            "state": "extract state (e.g. Ohio) from geographic location string",
            "country": "extract country (e.g. Canada, United States) from geographic location string ",
            "phase": "Extract the study phase if mentioned.",
            "study_type": "Identify the type of study if specified (e.g., interventional, observational).",
            "sponsor": "Extract the name of the sponsoring organization, if any.",
            "other_term": "Extract any other relevant terms that don't fit in any of the other fields.",
        }

        def is_field_filtered(field, value):
            if field == "sex":
                return value in ("FEMALE", "MALE")  # "All" means not filtered
            return bool(value)  # any non-empty value means filtered

        final_prompt_lines = []
        for field, description in field_descriptions.items():
            user_value = input_data.get(field, "")
            if not is_field_filtered(field, user_value):
                final_prompt_lines.append(description)
        
        # Join lines into final prompt
        final_prompt = "\n".join(final_prompt_lines)
        
        """Refine query"""
        if not self.client:
            return {"error": "LiteLLM client not initialized"}
            
        print("[QueryService] Generating patient query")
        
        try:
            prompt_system = self.load_prompt("build_default_patient_query_system.md", {})
            prompt_user = self.load_prompt("build_default_patient_query_user.md", {
                "patientQuery": input_data.get("user_query"),
                "promptLines": final_prompt
            })
            response = self.client.chat.completions.create(
                model="GPT-4o",
                messages=[
                    {"role": "system", "content": prompt_system},
                    {"role": "user", "content": prompt_user}
                ],
                response_format={"type": "json_object"},
                temperature=0
            )
            
            refined_query = response.choices[0].message.content.strip()
            try:
                parsed = json.loads(refined_query)
                final_data = {
                "cond": input_data.get("cond") or parsed.get("cond"),
                "intr": input_data.get("intr") or parsed.get("intr"),
                "sex": input_data.get("sex") or parsed.get("sex"),
                "age": input_data.get("age") or parsed.get("age"),
                "locStr": input_data.get("locStr") or parsed.get("locStr"),
                "city": input_data.get("city") or parsed.get("city"),
                "state": input_data.get("state") or parsed.get("state"),
                "country": input_data.get("country") or parsed.get("country"),
                "phase": input_data.get("phase") or parsed.get("phase"),
                "study_type": input_data.get("study_type") or parsed.get("study_type"),
                "sponsor": input_data.get("sponsor") or parsed.get("sponsor"),
                "other_term": input_data.get("other_term") or parsed.get("other_term"),
                "query": input_data.get("user_query") or parsed.get("query")
                }
                return final_data    
            except Exception as e:
                raise Exception("Failed to parse generated query response") from e
            
        except Exception as e:
            print(f"[QueryService] Query generation error: {e}")
            return {"error": f"Query generation failed: {e}"}
        
    def generate_patient_variations(self, input_data: dict) -> dict:
        if not self.client:
            return {"error": "LiteLLM client not initialized"}
            
        print("[QueryService] Generating expanded patient query")

        query_prompts = []
        x=1
        if input_data.get("intr"):
            rule = f"""Create a new query with a broader intervention:
            - Replace "intr" with its category (drug, device, behavioral, procedure, genetic, radiation, dietary supplement, diagnostic test, combination product, biological, or other).
            - If unable to classify, remove "intr".
            Type: Broadened Intervention"""
            query_prompts.append(f"{x}: {rule}")
            x+=1

            rule = f"""Create a new query with alternative interventions:
            - Pick a similar intervention (of the same class/type).
            - Remove "intr".
            - Add "original intervention OR alt intervention" to "other_term".
            Type: Additional Interventions"""
            query_prompts.append(f"{x}: {rule}")
            x+=1

        location_prompts = {
            "city": f"""If "city" exists → remove "city". Keep "state" and "country". 
                Type: Expanded Location (State)""",
            "state": f"""If "state" exists → remove "state". Keep "country". 
                Type: Expanded Location (Country)""",
            "country": f"""If "country" exists → remove all location fields. 
                Type: Expanded Location (Global)"""
        }
        for field, description in location_prompts.items():
            if input_data.get(field, ""):
                query_prompts.append(f"{x}: {description}")
                x+=1
        
        if input_data.get("age") or input_data.get("sex"):
            rule=f"""If "age" or "sex" exists → remove both fields. 
                Type: Modified Demographics"""
            query_prompts.append(f"{x}: {rule}")
            x+=1

        if input_data.get("sponsor") or input_data.get("phase") or input_data.get("study_type"):
            rule=f"""If "sponsor" or "phase" or "study_type" exists → remove all three. 
            Type: Modified Study Scope"""
            query_prompts.append(f"{x}: {rule}")
            x+=1

        if input_data.get("intr") and input_data.get("sex") and input_data.get("age") and (input_data.get("sponsor") or input_data.get("phase") or input_data.get("study_type")):
            rule=f"""If intr+age+sex+(sponsor/phase/study_type) exist:
            - Remove "sex", "age", "sponsor", "phase", "study_type".
            - Replace "intr" with the broadened intervention term.
            Type: Expanded + Broad Intervention"""
            query_prompts.append(f"{x}: {rule}")
            x+=1

            rule=f"""If intr+age+sex+(sponsor/phase/study_type) exist:
            - Remove "sex", "age", "sponsor", "phase", "study_type", "intr".
            - Add "other_term" = (original OR additional intervention string).
            Type: Expanded + Additional Interventions"""
            query_prompts.append(f"{x}: {rule}")
            x+=1

        if (input_data.get("state") or input_data.get("country")) and input_data.get("intr"):
            rule=f"""If intr+state/country exist:
            - Keep only "country". Remove "city"/"state".
            - Replace "intr" with broadened intervention term.
            Type: Broad Intervention + National"""
            query_prompts.append(f"{x}: {rule}")
            x+=1

            rule=f"""If intr+state/country exist:
            - Keep only "country". Remove "city"/"state" and "intr".
            - Add "other_term" = (original OR additional intervention string).
            Type: Additional Interventions + National"""
            query_prompts.append(f"{x}: {rule}")
            x+=1

            rule=f"""If intr+state/country exist:
            - Remove all location fields.
            - Replace "intr" with broadened intervention term.
            Type: Broad Intervention + Global"""
            query_prompts.append(f"{x}: {rule}")
            x+=1

            rule=f"""If intr+state/country exist:
            - Remove all location fields and "intr".
            - Add "other_term" = (original OR additional intervention string).
            Type: Additional Interventions + Global"""
            query_prompts.append(f"{x}: {rule}")
            x+=1

        try:
            prompt_system = self.load_prompt("generate_patient_queries_system.md", {})
            prompt_user = self.load_prompt("generate_patient_queries_user.md", {
                "inputData": json.dumps(input_data, ensure_ascii=False, indent=2),
                "queryRules": "\n".join(query_prompts)
            })
            response = self.client.chat.completions.create(
                model="GPT-4o",
                messages=[
                    {"role": "system", "content": prompt_system},
                    {"role": "user", "content": prompt_user}
                ],
                response_format={"type": "json_object"},
                temperature=0
            )
            
            refined_query = response.choices[0].message.content.strip()
            try:
                parsed = json.loads(refined_query)
                return parsed    
            except Exception as e:
                raise Exception("Failed to parse generated query response") from e        
        except Exception as e:
            print(f"[QueryService] Query generation error: {e}")
            return {"error": f"Query generation failed: {e}"}

    def generate_query_terms(self, input_data: dict) -> dict:
        try:
            prompt_system = self.load_prompt("build_dynamic_queries_system.md", {})
            prompt_user = self.load_prompt("build_dynamic_queries_user.md", {
                "inputData": json.dumps(input_data, ensure_ascii=False, indent=2),
            })
            response = self.client.chat.completions.create(
                model="GPT-4o",
                messages=[
                    {"role": "system", "content": prompt_system},
                    {"role": "user", "content": prompt_user}
                ],
                response_format={"type": "json_object"},
                temperature=0
            )
            
            query_terms = response.choices[0].message.content.strip()
            try:
                parsed = json.loads(query_terms)
                return parsed    
            except Exception as e:
                raise Exception("Failed to parse generated query response") from e        
        except Exception as e:
            print(f"[QueryService] Query generation error: {e}")
            return {"error": f"Query generation failed: {e}"}
    
# Global instance (singleton pattern)
_query_service = None

def get_query_service() -> QueryService:
    """Return global query service instance"""
    global _query_service
    if _query_service is None:
        _query_service = QueryService()
    return _query_service
