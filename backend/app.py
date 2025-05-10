"""
Salesforce AI Chatbot - FastAPI Backend
Main application entry point
"""
import os
import logging
import json
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
from agent import SalesforceAIAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Hardcoded Gemini API Key
GEMINI_API_KEY = "AIzaSyBlpyTc48FxdP7pzsPTK36EVO_Y0QKhkQg"

# Initialize the FastAPI app
app = FastAPI(
    title="Salesforce AI Chatbot API",
    description="Backend API for Salesforce AI Chatbot using Google Gemini",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific Salesforce domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the AI agent
ai_agent = SalesforceAIAgent()

class QueryRequest(BaseModel):
    query_text: str
    user_id: str
    username: str
    context: Optional[Dict[str, Any]] = None

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "online", "message": "Salesforce AI Chatbot API is running with Google Gemini"}

@app.post("/process_query")
async def process_query(request: QueryRequest):
    """
    Process a query from the Salesforce chatbot
    
    Args:
        request: The query request containing the text and context
        
    Returns:
        JSON response with the AI's answer
    """
    try:
        logger.info(f"Received query: {request.query_text}")
        
        # Process the query with the AI agent
        response = ai_agent.process_query(
            query_text=request.query_text,
            user_id=request.user_id,
            username=request.username,
            context=request.context
        )
        
        logger.info(f"Query processed successfully")
        return response
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

@app.get("/available_models")
async def available_models():
    """Returns information about available language models"""
    return {
        "models": ai_agent.get_available_models()
    }

@app.get("/ping")
async def ping():
    """Simple ping endpoint for connectivity tests"""
    return {"ping": "pong", "status": "ok", "model": "gemini-1.5-flash"}

if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment variable or use default
    port = int(os.environ.get("PORT", 8000))
    
    # Start the server
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=os.environ.get("ENV", "production") == "development"
    ) 