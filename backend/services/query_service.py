"""
Query Refinement Service

Responsible for improving user search queries.
"""

import os
import json
from typing import Dict
from openai import AzureOpenAI
from pathlib import Path


class QueryService:
    """Query refinement service using OpenAI"""
    
    def __init__(self):
        # Check environment variables
        self.azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY") 
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION")
        
        self.client = None
        
        # Validate environment variables
        missing_vars = []
        if not self.azure_endpoint:
            missing_vars.append("AZURE_OPENAI_ENDPOINT")
        if not self.api_key:
            missing_vars.append("AZURE_OPENAI_API_KEY")
        if not self.api_version:
            missing_vars.append("AZURE_OPENAI_API_VERSION")
            
        if missing_vars:
            print(f"⚠️  Warning: OpenAI environment variables not set: {', '.join(missing_vars)}")
            print("   Query refinement feature will be disabled.")
            return
        
        # Initialize client
        try:
            self.client = AzureOpenAI(
                azure_endpoint=self.azure_endpoint,
                api_key=self.api_key,
                api_version=self.api_version
            )
            print("✅ OpenAI query refinement client initialized")
        except Exception as e:
            print(f"⚠️  Warning: Failed to initialize OpenAI query refinement client: {e}")
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
            return {"error": "OpenAI client not initialized"}
            
        print("[QueryService] Refining query")
        
        try:
            prompt_system = self.load_prompt("refine_query_prompt_system.md", {})
            prompt_user = self.load_prompt("refine_query_prompt_user.md", {
                "inputData": json.dumps(input_data, ensure_ascii=False, indent=2)
            })
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": prompt_system},
                    {"role": "user", "content": prompt_user}
                ],
                response_format={"type": "json_object"}
            )
            
            refined_query = response.choices[0].message.content.strip()
            try:
                parsed = json.loads(refined_query)
            except Exception as e:
                raise Exception("Failed to parse Refined Query response") from e
            return parsed
            
        except Exception as e:
            print(f"[QueryService] Query refinement error: {e}")
            return {"error": f"Query refinement failed: {e}"}


# Global instance (singleton pattern)
_query_service = None

def get_query_service() -> QueryService:
    """Return global query service instance"""
    global _query_service
    if _query_service is None:
        _query_service = QueryService()
    return _query_service
