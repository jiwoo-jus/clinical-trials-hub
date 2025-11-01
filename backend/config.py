import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# LiteLLM Configuration (replaced Azure OpenAI)
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY")
LITELLM_BASE_URL = os.getenv("LITELLM_BASE_URL")

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

NCBI_API_INFO = [ [NCBI_API_KEY, NCBI_API_EMAIL], [NCBI_API_KEY2, NCBI_API_EMAIL2], [NCBI_API_KEY3, NCBI_API_EMAIL3] ]

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
