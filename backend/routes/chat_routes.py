from fastapi import APIRouter, HTTPException, Request, Body # Import Body
from pydantic import BaseModel, Field # Import Pydantic models
from services import pm_service, pmc_service
from services.chat_service import get_chat_service

router = APIRouter()

# Define request model for better validation
class ChatRequest(BaseModel):
    userQuestion: str
    source: str = Field(..., pattern="^(CTG|PM|PMC)$") # Validate source
    id: str # nctId or pmcid
    content: str # Can be JSON string or HTML/text

@router.post("")
# Use the Pydantic model for automatic validation
async def chat_about_paper(chat_request: ChatRequest):
    try:
        print(f"Received chat request for source: {chat_request.source}, id: {chat_request.id}")
        # Data is already validated and parsed by Pydantic
        user_question = chat_request.userQuestion
        paper_content = chat_request.content
        source = chat_request.source
        # id = chat_request.id # ID is available if needed later

        # Pass source to the chat service
        chat_service = get_chat_service()
        result = chat_service.chat_about_paper(source, paper_content, user_question)

        if "highlighted_article" in result:
            del result["highlighted_article"]

        return result
    except Exception as e:
        print(f"Error in chat route: {type(e).__name__} - {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error processing chat request: {str(e)}")