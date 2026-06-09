import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def _get_env(name: str, default=None):
    """Read env vars while also accepting lowercase keys from YAML-style configs."""
    value = os.getenv(name)
    if value is not None and value != "":
        return value
    value = os.getenv(name.lower())
    if value is not None and value != "":
        return value
    return default


def _get_float_env(name: str, default: float) -> float:
    try:
        return float(_get_env(name, default))
    except (TypeError, ValueError):
        return default


def _get_int_env(name: str, default: int) -> int:
    try:
        return int(_get_env(name, default))
    except (TypeError, ValueError):
        return default


def _is_placeholder(value) -> bool:
    if not value:
        return False
    normalized = value.strip().strip('"').strip("'").lower()
    return normalized.startswith("your_") or normalized.endswith("_here")


def _has_value(value) -> bool:
    return bool(value) and not _is_placeholder(value)


# LLM Provider / Router Configuration
# Supported values: "litellm", "azure"
LLM_PROVIDER = _get_env("LLM_PROVIDER", "litellm").strip().lower()
LLM_DEFAULT_MODEL = _get_env("LLM_DEFAULT_MODEL") or _get_env("AZURE_OPENAI_DEPLOYMENT") or "GPT-5"
LLM_QUERY_MODEL = _get_env("LLM_QUERY_MODEL", LLM_DEFAULT_MODEL)
LLM_CHAT_MODEL = _get_env("LLM_CHAT_MODEL", LLM_DEFAULT_MODEL)
LLM_INSIGHTS_MODEL = _get_env("LLM_INSIGHTS_MODEL", LLM_DEFAULT_MODEL)
LLM_SYSTEMATIC_REVIEW_MODEL = _get_env("LLM_SYSTEMATIC_REVIEW_MODEL", LLM_DEFAULT_MODEL)
LLM_EXTRACTION_MODEL = _get_env("LLM_EXTRACTION_MODEL", LLM_DEFAULT_MODEL)
LLM_METADATA_MODEL = _get_env("LLM_METADATA_MODEL", LLM_DEFAULT_MODEL)
LLM_REQUEST_TIMEOUT = _get_float_env("LLM_REQUEST_TIMEOUT", 180.0)
LLM_USE_RESPONSE_FORMAT = _get_env("LLM_USE_RESPONSE_FORMAT", "auto").strip().lower()
LLM_USE_TEMPERATURE = _get_env("LLM_USE_TEMPERATURE", "auto").strip().lower()
LLM_USE_SEED = _get_env("LLM_USE_SEED", "false").strip().lower()
LLM_EXTRACTION_CONCURRENCY = max(1, _get_int_env("LLM_EXTRACTION_CONCURRENCY", 3))

# LiteLLM Configuration
LITELLM_API_KEY = _get_env("LITELLM_API_KEY")
LITELLM_BASE_URL = _get_env("LITELLM_BASE_URL")

# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT = _get_env("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = _get_env("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_VERSION = _get_env("AZURE_OPENAI_API_VERSION", "2024-10-21")
AZURE_OPENAI_DEPLOYMENT = _get_env("AZURE_OPENAI_DEPLOYMENT")

# NCBI API Configuration
NCBI_API_KEY = os.getenv("NCBI_API_KEY")
NCBI_API_EMAIL = os.getenv("NCBI_API_EMAIL")
NCBI_TOOL_NAME = os.getenv("NCBI_TOOL_NAME")

NCBI_API_KEY = os.getenv("NCBI_API_KEY")
NCBI_API_EMAIL = os.getenv("NCBI_API_EMAIL")

NCBI_API_KEY2 = os.getenv("NCBI_API_KEY2")
NCBI_API_EMAIL2 =  os.getenv("NCBI_API_EMAIL2")

NCBI_API_KEY3 = os.getenv("NCBI_API_KEY3")
NCBI_API_EMAIL3 =  os.getenv("NCBI_API_EMAIL3")

NCBI_API_INFO = [
    [api_key, email]
    for api_key, email in [
        [NCBI_API_KEY, NCBI_API_EMAIL],
        [NCBI_API_KEY2, NCBI_API_EMAIL2],
        [NCBI_API_KEY3, NCBI_API_EMAIL3],
    ]
    if (not api_key or _has_value(api_key)) and (not email or _has_value(email))
]
if not NCBI_API_INFO:
    NCBI_API_INFO = [[None, None]]

# Database Configuration
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# Server Configuration
PORT = int(os.getenv("PORT", 5050))

# CORS Configuration
RAW_CORS_ORIGINS = os.getenv("CORS_ORIGINS", "")
CORS_ORIGINS = [origin.strip() for origin in RAW_CORS_ORIGINS.split(",") if origin.strip()]

# Redis Configuration (Optional - for caching)
REDIS_URL = os.getenv("REDIS_URL")

# Pagination Configuration
MAX_FETCH_SIZE = int(os.getenv("MAX_FETCH_SIZE", 1000))
DEFAULT_PAGE_SIZE = int(os.getenv("DEFAULT_PAGE_SIZE", 10))
