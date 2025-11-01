from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from services.insights_service import InsightsService
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class GenerateInsightsRequest(BaseModel):
    search_key: str
    page: Optional[int] = 1
    applied_filters: Optional[Dict[str, Any]] = None

class ChatMessage(BaseModel):
    role: str
    message: str

class ChatRequest(BaseModel):
    search_key: str
    message: str
    page: Optional[int] = 1
    chat_history: Optional[List[ChatMessage]] = []
    applied_filters: Optional[Dict[str, Any]] = None

@router.post("/generate-insights")
async def generate_insights(request: GenerateInsightsRequest):
    """
    Generate AI insights for search results
    """
    try:
        logger.info(f"Generating insights for search_key: {request.search_key}, page: {request.page}")
        
        # Generate insights using the service
        insights_service = InsightsService()
        result = insights_service.generate_insights(
            search_key=request.search_key,
            page=request.page,
            applied_filters=request.applied_filters
        )
        
        if result.get('error'):
            raise HTTPException(status_code=400, detail=result['error'])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating insights: {str(e)}")
        raise HTTPException(status_code=500, detail='Failed to generate insights')

@router.post("/chat")
async def chat_with_insights(request: ChatRequest):
    """
    Chat about the insights and search results
    """
    try:
        logger.info(f"Chat request for search_key: {request.search_key}, message: {request.message[:100]}...")
        
        # Convert chat history to dict format
        chat_history = [{'role': msg.role, 'message': msg.message} for msg in request.chat_history]
        
        # Process chat using the service
        insights_service = InsightsService()
        result = insights_service.chat_about_results(
            search_key=request.search_key,
            message=request.message,
            page=request.page,
            chat_history=chat_history,
            applied_filters=request.applied_filters
        )
        
        if result.get('error'):
            raise HTTPException(status_code=400, detail=result['error'])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat: {str(e)}")
        raise HTTPException(status_code=500, detail='Failed to process chat message')
