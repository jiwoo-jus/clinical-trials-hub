import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

import openai

import config

logger = logging.getLogger(__name__)

SUPPORTED_PROVIDERS = {"litellm", "azure"}


@dataclass(frozen=True)
class LLMSettings:
    provider: str
    default_model: str
    task_models: Dict[str, str]
    litellm_api_key: Optional[str]
    litellm_base_url: Optional[str]
    azure_endpoint: Optional[str]
    azure_api_key: Optional[str]
    azure_api_version: Optional[str]
    azure_deployment: Optional[str]
    timeout: float
    use_response_format: str
    use_temperature: str
    use_seed: str

    @property
    def provider_label(self) -> str:
        if self.provider == "azure":
            return "Azure OpenAI"
        if self.provider == "litellm":
            return "LiteLLM"
        return self.provider

    def model_for_task(self, task: Optional[str] = None) -> str:
        if task and self.task_models.get(task):
            return self.task_models[task]
        return self.default_model

    def missing_variables(self) -> list[str]:
        if self.provider == "litellm":
            required = {
                "LITELLM_API_KEY": self.litellm_api_key,
                "LITELLM_BASE_URL": self.litellm_base_url,
            }
        elif self.provider == "azure":
            required = {
                "AZURE_OPENAI_ENDPOINT": self.azure_endpoint,
                "AZURE_OPENAI_API_KEY": self.azure_api_key,
                "AZURE_OPENAI_API_VERSION": self.azure_api_version,
                "AZURE_OPENAI_DEPLOYMENT": self.azure_deployment,
            }
        else:
            return [f"LLM_PROVIDER must be one of: {', '.join(sorted(SUPPORTED_PROVIDERS))}"]

        return [name for name, value in required.items() if not value]

    @property
    def is_configured(self) -> bool:
        return self.provider in SUPPORTED_PROVIDERS and not self.missing_variables()


def _normalize_provider(provider: str) -> str:
    normalized = (provider or "litellm").strip().lower().replace("-", "_")
    if normalized in {"azure_openai", "azureopenai"}:
        return "azure"
    return normalized


def get_llm_settings() -> LLMSettings:
    provider = _normalize_provider(config.LLM_PROVIDER)
    default_model = config.LLM_DEFAULT_MODEL
    if provider == "azure":
        default_model = default_model or config.AZURE_OPENAI_DEPLOYMENT

    task_models = {
        "query": config.LLM_QUERY_MODEL or default_model,
        "chat": config.LLM_CHAT_MODEL or default_model,
        "insights": config.LLM_INSIGHTS_MODEL or default_model,
        "systematic_review": config.LLM_SYSTEMATIC_REVIEW_MODEL or default_model,
        "extraction": config.LLM_EXTRACTION_MODEL or default_model,
        "metadata": config.LLM_METADATA_MODEL or default_model,
    }

    return LLMSettings(
        provider=provider,
        default_model=default_model,
        task_models=task_models,
        litellm_api_key=config.LITELLM_API_KEY,
        litellm_base_url=config.LITELLM_BASE_URL,
        azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
        azure_api_key=config.AZURE_OPENAI_API_KEY,
        azure_api_version=config.AZURE_OPENAI_API_VERSION,
        azure_deployment=config.AZURE_OPENAI_DEPLOYMENT,
        timeout=config.LLM_REQUEST_TIMEOUT,
        use_response_format=config.LLM_USE_RESPONSE_FORMAT,
        use_temperature=config.LLM_USE_TEMPERATURE,
        use_seed=config.LLM_USE_SEED,
    )


def create_chat_client(async_client: bool = False, timeout: Optional[float] = None):
    settings = get_llm_settings()
    if not settings.is_configured:
        missing = ", ".join(settings.missing_variables())
        logger.warning("%s client not initialized. Missing configuration: %s", settings.provider_label, missing)
        return None, settings

    request_timeout = timeout or settings.timeout

    if settings.provider == "azure":
        if async_client:
            client_cls = getattr(openai, "AsyncAzureOpenAI", None)
        else:
            client_cls = getattr(openai, "AzureOpenAI", None)
        if client_cls is None:
            raise RuntimeError("Installed openai package does not provide AzureOpenAI clients.")
        client = client_cls(
            api_key=settings.azure_api_key,
            azure_endpoint=settings.azure_endpoint,
            api_version=settings.azure_api_version,
            timeout=request_timeout,
        )
    else:
        client_cls = openai.AsyncOpenAI if async_client else openai.OpenAI
        client = client_cls(
            api_key=settings.litellm_api_key,
            base_url=settings.litellm_base_url,
            timeout=request_timeout,
        )

    logger.info("%s client initialized", settings.provider_label)
    return client, settings


def _is_gpt5_like(model: str) -> bool:
    normalized = (model or "").strip().lower().replace("_", "-")
    return normalized.startswith("gpt-5")


def _enabled(setting: str, default: bool) -> bool:
    value = (setting or "auto").strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return default


def _should_include_response_format(settings: LLMSettings, model: str) -> bool:
    return _enabled(settings.use_response_format, default=not _is_gpt5_like(model))


def _should_include_temperature(settings: LLMSettings, model: str) -> bool:
    return _enabled(settings.use_temperature, default=not _is_gpt5_like(model))


def _should_include_seed(settings: LLMSettings) -> bool:
    return _enabled(settings.use_seed, default=False)


def build_chat_completion_params(
    settings: LLMSettings,
    *,
    task: Optional[str],
    messages: list[dict[str, str]],
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    response_format: Optional[str | dict[str, Any]] = None,
    stream: bool = False,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    model = settings.model_for_task(task)
    params: Dict[str, Any] = {
        "model": model,
        "messages": messages,
    }

    if max_tokens is not None:
        if settings.provider == "azure" and _is_gpt5_like(model):
            params["max_completion_tokens"] = max_tokens
        else:
            params["max_tokens"] = max_tokens
    if stream:
        params["stream"] = True
    if temperature is not None and _should_include_temperature(settings, model):
        params["temperature"] = temperature
    if seed is not None and _should_include_seed(settings):
        params["seed"] = seed
    if response_format and _should_include_response_format(settings, model):
        if response_format == "json":
            params["response_format"] = {"type": "json_object"}
        elif isinstance(response_format, dict):
            params["response_format"] = response_format

    return params


def _retry_params_after_unsupported_argument_error(params: Dict[str, Any], error: Exception) -> Optional[Dict[str, Any]]:
    message = str(error).lower()
    retry_params = dict(params)
    changed = False

    for key in ("response_format", "temperature", "seed"):
        if key in retry_params and key in message:
            retry_params.pop(key, None)
            changed = True

    if "max_tokens" in retry_params and "max_completion_tokens" in message:
        retry_params["max_completion_tokens"] = retry_params.pop("max_tokens")
        changed = True

    return retry_params if changed else None


def create_chat_completion(client, settings: LLMSettings, params: Dict[str, Any]):
    try:
        return client.chat.completions.create(**params)
    except Exception as error:
        retry_params = _retry_params_after_unsupported_argument_error(params, error)
        if retry_params:
            logger.warning("Retrying %s request after removing unsupported LLM parameter: %s", settings.provider_label, error)
            return client.chat.completions.create(**retry_params)
        raise


async def create_async_chat_completion(client, settings: LLMSettings, params: Dict[str, Any]):
    try:
        return await client.chat.completions.create(**params)
    except Exception as error:
        retry_params = _retry_params_after_unsupported_argument_error(params, error)
        if retry_params:
            logger.warning("Retrying %s request after removing unsupported LLM parameter: %s", settings.provider_label, error)
            return await client.chat.completions.create(**retry_params)
        raise


def strip_markdown_code_fences(text: str) -> str:
    result = (text or "").strip()
    if not result.startswith("```"):
        return result

    lines = result.splitlines()
    lines = [line for line in lines if not line.strip().startswith("```")]
    return "\n".join(lines).strip()
