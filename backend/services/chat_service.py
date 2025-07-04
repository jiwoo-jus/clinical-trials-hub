"""
Chat Service

Responsible for the question and answer function regarding the content of the paper
"""

import os
import json
from typing import Dict
from openai import AzureOpenAI
from pathlib import Path


class ChatService:
    """Q&A service for papers using OpenAI"""
    
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
            print(f"⚠️  Warning: OpenAI environment variables are not set: {', '.join(missing_vars)}")
            print("   Chat function will be disabled.")
            return
        
        # Initialize client
        try:
            self.client = AzureOpenAI(
                azure_endpoint=self.azure_endpoint,
                api_key=self.api_key,
                api_version=self.api_version
            )
            print("✅ OpenAI chat client initialization complete")
        except Exception as e:
            print(f"⚠️  Warning: OpenAI chat client initialization failed: {e}")
            self.client = None
    
    def load_prompt(self, file_name: str, variables: dict) -> str:
        """Load prompt template and replace variables"""
        # Path from services to prompts directory
        prompt_path = Path(__file__).parent.parent / "prompts" / file_name
        
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                template = f.read()
        except Exception as e:
            raise Exception(f"Error reading prompt file ({prompt_path}): {e}")
        
        # Replace variables
        for key, value in variables.items():
            template = template.replace(f"{{{{{key}}}}}", str(value))
        
        return template
    
    def chat_with_prompt(self, prompt_template_name: str, variables: dict) -> dict:
        """Chat using prompt template"""
        if not self.client:
            return {"answer": "Error: OpenAI client not initialized", "evidence": []}
            
        try:
            prompt = self.load_prompt(prompt_template_name, variables)
            user_question = variables.get("userQuestion", "N/A")
            
            print(f"[ChatService] Template: {prompt_template_name}, User Question: {user_question}")
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant answering questions based on provided clinical trial information."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            result_text = response.choices[0].message.content.strip()
            
            try:
                parsed = json.loads(result_text)
                if not isinstance(parsed, dict) or "answer" not in parsed or "evidence" not in parsed:
                    parsed = {"answer": "Error: Received unexpected format from AI.", "evidence": []}
                return parsed
            except json.JSONDecodeError:
                return {"answer": result_text, "evidence": []}
                
        except Exception as e:
            print(f"[ChatService] API error: {e}")
            return {"answer": f"Error communicating with AI service: {e}", "evidence": []}
    
    def chat_about_paper(self, source: str, paper_content: str, user_question: str) -> dict:
        """Q&A about the paper"""
        if not self.client:
            return {"answer": "Error: OpenAI client not initialized", "evidence": []}
            
        if source == 'CTG':
            try:
                json.loads(paper_content)
                variables = {"structuredInfo": paper_content, "userQuestion": user_question}
                return self.chat_with_prompt("chatAboutCtgStructuredInfo.md", variables)
            except json.JSONDecodeError:
                return {"answer": "Error: Could not process the provided ClinicalTrials.gov data (invalid format).", "evidence": []}
        elif source in ['PM', 'PMC']:
            variables = {"paperContent": paper_content, "userQuestion": user_question}
            return self.chat_with_prompt("chatAboutPaper.md", variables)
        else:
            return {"answer": f"Error: Unknown data source '{source}'.", "evidence": []}


# Global instance (singleton pattern)
_chat_service = None

def get_chat_service() -> ChatService:
    """Return global chat service instance"""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service
