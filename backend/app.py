import os
import sys
import logging
from datetime import datetime
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import search_routes, paper_routes, chat_routes, utils_routes, insights_routes
from config import PORT, CORS_ORIGINS

# Create log directory and configure logging
log_dir = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(log_dir, exist_ok=True)
current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_file = os.path.join(log_dir, f"log_{current_time}.log")

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Set to DEBUG for more detailed logs. Default is INFO.
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # Logs to console
        logging.FileHandler(log_file, mode="a", encoding="utf-8")  # Logs to file
    ]
)

logger = logging.getLogger(__name__)

# Test logging
logger.info("[Test] Logging system initialized.")
logger.debug("[Test] This is a debug message.")
logger.error("[Test] This is an error message.")

# Redirect stdout and stderr to logger
class LoggerWriter:
    def __init__(self, level):
        self.level = level

    def write(self, message):
        if message.strip():
            self.level(message.strip())

    def flush(self):
        pass
    
    def isatty(self):
        return False

sys.stdout = LoggerWriter(logger.info)
sys.stderr = LoggerWriter(logger.error)

# Initialize FastAPI app
app = FastAPI()

# Configure CORS from environment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(search_routes.router, prefix="/api/search")
app.include_router(paper_routes.router, prefix="/api/paper")
app.include_router(chat_routes.router, prefix="/api/chat")
app.include_router(utils_routes.router, prefix="/api/utils", tags=["utilities"])
app.include_router(insights_routes.router, prefix="/api/insights", tags=["insights"])

@app.get("/test")
async def test_endpoint():
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    logger.info(f"Test endpoint accessed at {current_time}")
    return {"message": "CORS works!"}

@app.get("/cors-check")
def cors_check():
    from fastapi.responses import JSONResponse
    import os
    return JSONResponse(
        content={
            "CORS_ORIGINS": CORS_ORIGINS,
            "CORS_ORIGINS_env": os.getenv("CORS_ORIGINS"),
            "effective_allow_origins": ["*"]
        }
    )

# Local development entry point
if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting server on port {PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT, proxy_headers=True)