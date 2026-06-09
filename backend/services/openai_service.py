import logging
from services.llm_client import (
    build_chat_completion_params,
    create_chat_client,
    create_chat_completion,
    strip_markdown_code_fences,
)

logger = logging.getLogger(__name__)
insights_log = logging.getLogger("insights_conversations")  # Reference to dedicated logger

class OpenAIService:
    def __init__(self, model_task: str = "insights"):
        self.model_task = model_task
        try:
            self.client, self.llm_settings = create_chat_client()
            if self.client:
                logger.info("✅ %s client initialized", self.llm_settings.provider_label)
            else:
                logger.warning("%s client not available. Using mock response.", self.llm_settings.provider_label)
        except Exception as e:
            logger.warning(f"Failed to initialize LLM client: {e}")
            self.client = None
            self.llm_settings = None
        
    def generate_completion(self, prompt: str, system_message: str = None, 
                          max_tokens: int = 1000, temperature: float = 0, 
                          response_format: str = None, model_task: str = None) -> str:
        """
        Generate a completion using the configured LLM provider.
        """
        try:
            if not self.client:
                # Return mock response for testing
                logger.info("Using mock response (LLM client not available)")
                mock = self._generate_mock_response(prompt)

                # ── Log: mock response ──────────────────────────────────────
                insights_log.info("━" * 80)
                insights_log.info("[OPENAI REQUEST] ※ Mock mode (LLM client not available)")
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
            task = model_task or self.model_task
            model = self.llm_settings.model_for_task(task)

            # ── Log: before actual API request ──────────────────────────────
            insights_log.info("━" * 80)
            insights_log.info(f"[OPENAI REQUEST] → {self.llm_settings.provider_label} API call")
            insights_log.info(f"  provider   : {self.llm_settings.provider}")
            insights_log.info(f"  model      : {model}")
            insights_log.info(f"  task       : {task}")
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
            
            logger.info("Calling %s API...", self.llm_settings.provider_label)
            
            request_params = build_chat_completion_params(
                self.llm_settings,
                task=task,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                response_format=response_format,
            )
            response = create_chat_completion(self.client, self.llm_settings, request_params)
            
            result = response.choices[0].message.content
            result = strip_markdown_code_fences(result)

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

            logger.info("✅ %s API call successful", self.llm_settings.provider_label)
            return result
            
        except Exception as e:
            logger.error(f"Error generating LLM completion: {str(e)}")
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
