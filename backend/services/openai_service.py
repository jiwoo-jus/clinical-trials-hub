import os
import json
import logging
from typing import Optional
import openai

logger = logging.getLogger(__name__)
insights_log = logging.getLogger("insights_conversations")  # Reference to dedicated logger

class OpenAIService:
    def __init__(self):
        # Check LiteLLM environment variables
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
            logger.warning(f"LiteLLM environment variables not set: {', '.join(missing_vars)}")
            logger.warning("Using mock response.")
            return
        
        # Initialize LiteLLM client
        try:
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger.info("✅ LiteLLM client initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize LiteLLM client: {e}")
            self.client = None
        
    def generate_completion(self, prompt: str, system_message: str = None, 
                          max_tokens: int = 1000, temperature: float = 0, 
                          response_format: str = None) -> str:
        """
        Generate a completion using LiteLLM's Chat API
        """
        try:
            if not self.client:
                # Return mock response for testing
                logger.info("Using mock response (LiteLLM client not available)")
                mock = self._generate_mock_response(prompt)

                # ── Log: mock response ──────────────────────────────────────
                insights_log.info("━" * 80)
                insights_log.info("[OPENAI REQUEST] ※ Mock mode (LiteLLM client not available)")
                if system_message:
                    insights_log.info("── SYSTEM MESSAGE ──")
                    insights_log.info(system_message)
                insights_log.info("── USER PROMPT ──")
                insights_log.info(prompt)
                insights_log.info("── MOCK RESPONSE ──")
                insights_log.info(mock)
                insights_log.info("━" * 80)
                # ────────────────────────────────────────────────────────

                return mock
            
            messages = []
            
            if system_message:
                messages.append({"role": "system", "content": system_message})
            
            messages.append({"role": "user", "content": prompt})

            # ── Log: before actual API request ──────────────────────────────
            insights_log.info("━" * 80)
            insights_log.info("[OPENAI REQUEST] → LiteLLM API call")
            insights_log.info(f"  model      : GPT-5")
            insights_log.info(f"  max_tokens : {max_tokens}")
            insights_log.info(f"  temperature: {temperature}")
            insights_log.info(f"  response_format: {response_format}")
            if system_message:
                insights_log.info("── SYSTEM MESSAGE ──")
                insights_log.info(system_message)
            insights_log.info("── USER PROMPT ──")
            insights_log.info(prompt)
            insights_log.info("── (API call in progress) ──")
            # ────────────────────────────────────────────────────────────
            
            logger.info("Calling LiteLLM API...")
            
            # Prepare request parameters
            request_params = {
                "model": "GPT-5",
                "messages": messages,
                "max_tokens": max_tokens,
                # "temperature": temperature  # GPT-5: temperature not supported, using system default
            }
            
            # response_format json_object: not supported in GPT-5, so not used
            # Instead, JSON response is requested via the prompt
            # if response_format == "json":
            #     request_params["response_format"] = {"type": "json_object"}
            
            response = self.client.chat.completions.create(**request_params)
            
            result = response.choices[0].message.content
            result = result.strip() if result else ""

            # Strip markdown code fences (GPT-5 doesn't support response_format=json_object)
            if result.startswith("```"):
                lines = result.splitlines()
                # Remove opening fence (```json or ```) and closing fence (```)
                lines = [l for l in lines if not l.strip().startswith("```")]
                result = "\n".join(lines).strip()

            # ── Log: actual API response ─────────────────────────────────────
            usage = getattr(response, "usage", None)
            finish_reason = response.choices[0].finish_reason if response.choices else "unknown"
            if usage:
                insights_log.info(f"  [usage] prompt_tokens={usage.prompt_tokens}, "
                                  f"completion_tokens={usage.completion_tokens}, "
                                  f"total_tokens={usage.total_tokens}")
            insights_log.info(f"  [finish_reason] {finish_reason}")
            if finish_reason == "length":
                insights_log.warning("  ⚠️  finish_reason=length: Response was truncated by max_tokens! High risk of JSON parsing failure. Consider increasing max_tokens.")
            if not result:
                insights_log.error("  ❌ Response is empty (content=None or empty)")
            insights_log.info("── RAW RESPONSE ──")
            insights_log.info(result)
            insights_log.info("━" * 80)
            # ────────────────────────────────────────────────────────────

            logger.info("✅ LiteLLM API call successful")
            return result
            
        except Exception as e:
            logger.error(f"Error generating LiteLLM completion: {str(e)}")
            insights_log.error(f"[OPENAI REQUEST ERROR] {str(e)}")
            logger.info("Falling back to mock response")
            return self._generate_mock_response(prompt)
    
    def _generate_mock_response(self, prompt: str) -> str:
        """Generate a mock response for testing purposes"""
        if "insights" in prompt.lower():
            return """
{
    "summary": "This analysis covers a diverse range of clinical research spanning multiple therapeutic areas including oncology, cardiology, and infectious diseases. The research demonstrates a strong focus on innovative therapeutic approaches with significant recent activity.",
    "key_findings": [
        "High concentration of Phase II/III trials suggesting mature research pipeline",
        "Strong representation from major academic medical centers and pharmaceutical companies",
        "Notable focus on personalized medicine and targeted therapies",
        "Emerging trends in combination therapy approaches"
    ],
    "trends": [
        "Increasing adoption of biomarker-driven patient selection",
        "Growing emphasis on real-world evidence collection",
        "Shift towards adaptive trial designs"
    ],
    "recommendations": [
        "Consider exploring underrepresented patient populations",
        "Investigate potential for companion diagnostic development",
        "Monitor emerging safety signals across similar compounds"
    ],
    "research_gaps": [
        "Limited pediatric population studies",
        "Need for longer-term follow-up data",
        "Insufficient representation of diverse ethnic groups"
    ]
}
"""
        else:
            return "I can help you understand the clinical research data. Based on the search results, I can provide insights about study designs, patient populations, therapeutic approaches, and research trends. What specific aspect would you like to explore?"
