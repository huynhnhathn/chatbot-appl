from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uuid
import time
import os
from typing import Dict, Any, Optional

from app.models import (
    ChatRequest, ChatResponse, KnowledgeBaseRequest, KnowledgeBaseResponse,
    SearchRequest, SearchResponse, HealthCheckResponse, ErrorResponse
)
from app.chatbot import chatbot_engine
from app.database import db_manager
from app.middleware import setup_middleware
from app.monitoring import metrics_collector, HealthChecker, metrics_endpoint, get_metrics_summary
from app.logger import get_logger
from config import settings

logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Production-ready chatbot application with LangChain-OpenAI and Qdrant vector database",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Setup middleware
setup_middleware(app)

# Initialize health checker
health_checker = HealthChecker(db_manager, chatbot_engine)

# Templates for web interface
def get_templates_directory():
    """Get the templates directory path."""
    # Try multiple possible paths
    possible_paths = [
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"),
        os.path.join(os.getcwd(), "templates"),
        "templates"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            logger.info(f"Using templates directory: {path}")
            return path
    
    # Fallback to current directory
    logger.warning(f"Templates directory not found in any of: {possible_paths}")
    return "templates"

templates = Jinja2Templates(directory=get_templates_directory())


@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info("Application starting up", version=settings.app_version)
    
    # Verify database connection
    try:
        db_healthy = db_manager.health_check()
        if not db_healthy:
            logger.error("Database health check failed on startup")
        else:
            logger.info("Database connection verified")
    except Exception as e:
        logger.error("Database connection failed on startup", error=str(e))


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("Application shutting down")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root endpoint with web interface."""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "app_name": settings.app_name}
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint."""
    start_time = time.time()
    
    try:
        # Record metrics
        metrics_collector.record_chat_request()
        
        # Generate response
        result = chatbot_engine.generate_response(
            user_input=request.message,
            user_id=request.user_id
        )
        
        # Record response metrics
        metrics_collector.record_chat_response(
            tokens=result["tokens_used"],
            cost=result["cost"],
            response_time=result["response_time"]
        )
        
        # Create response
        response = ChatResponse(
            response=result["response"],
            context_used=result["context_used"],
            response_time=result["response_time"],
            tokens_used=result["tokens_used"],
            cost=result["cost"],
            error=result.get("error") if result else None,
            session_id=request.session_id
        )
        
        logger.info(
            "Chat request processed successfully",
            user_id=request.user_id,
            response_time=result["response_time"],
            tokens_used=result["tokens_used"]
        )
        
        return response
        
    except Exception as e:
        metrics_collector.record_error("chat_error")
        logger.error("Error in chat endpoint", error=str(e), user_id=request.user_id)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/knowledge-base", response_model=KnowledgeBaseResponse)
async def add_to_knowledge_base(request: KnowledgeBaseRequest):
    """Add content to knowledge base."""
    try:
        success = chatbot_engine.add_to_knowledge_base(
            content=request.content,
            metadata=request.metadata,
            source=request.source
        )
        
        if success:
            return KnowledgeBaseResponse(
                success=True,
                message="Content added to knowledge base successfully",
                document_id=str(uuid.uuid4())
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to add content to knowledge base")
            
    except Exception as e:
        metrics_collector.record_error("knowledge_base_error")
        logger.error("Error adding to knowledge base", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/search", response_model=SearchResponse)
async def search_knowledge_base(request: SearchRequest):
    """Search knowledge base."""
    try:
        results = db_manager.search_similar(
            query=request.query,
            limit=request.limit,
            score_threshold=request.score_threshold
        )
        
        # Convert to response model
        search_results = []
        for result in results:
            search_results.append({
                "id": str(result["id"]),
                "score": result["score"],
                "content": result["content"],
                "metadata": result["metadata"],
                "source": result["source"],
                "timestamp": result["timestamp"]
            })
        
        return SearchResponse(
            results=search_results,
            total_results=len(search_results),
            query=request.query
        )
        
    except Exception as e:
        metrics_collector.record_error("search_error")
        logger.error("Error searching knowledge base", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint."""
    try:
        health_status = await health_checker.check_health()
        
        return HealthCheckResponse(
            status=health_status["status"],
            timestamp=health_status["timestamp"],
            version=health_status["version"],
            database_healthy=health_status["components"]["database"]["status"] == "healthy",
            openai_healthy=health_status["components"]["openai"]["status"] == "healthy",
            uptime=health_status["uptime"]
        )
        
    except Exception as e:
        logger.error("Error in health check", error=str(e))
        raise HTTPException(status_code=500, detail="Health check failed")


@app.get("/api/metrics")
async def get_metrics():
    """Get application metrics."""
    try:
        metrics_summary = get_metrics_summary()
        return JSONResponse(content=metrics_summary)
    except Exception as e:
        logger.error("Error getting metrics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")


@app.get("/metrics")
async def prometheus_metrics(request: Request):
    """Prometheus metrics endpoint."""
    return await metrics_endpoint(request)


@app.delete("/api/knowledge-base")
async def clear_knowledge_base():
    """Clear all documents from knowledge base."""
    try:
        db_manager.delete_documents()
        logger.info("Knowledge base cleared")
        return {"message": "Knowledge base cleared successfully"}
    except Exception as e:
        metrics_collector.record_error("clear_knowledge_base_error")
        logger.error("Error clearing knowledge base", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to clear knowledge base")


@app.post("/api/chat/clear")
async def clear_chat_memory():
    """Clear chat conversation memory."""
    try:
        chatbot_engine.clear_memory()
        logger.info("Chat memory cleared")
        return {"message": "Chat memory cleared successfully"}
    except Exception as e:
        logger.error("Error clearing chat memory", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to clear chat memory")


@app.get("/api/info")
async def get_app_info():
    """Get application information."""
    try:
        collection_info = db_manager.get_collection_info()
        memory_summary = chatbot_engine.get_memory_summary()
        
        return {
            "app_name": settings.app_name,
            "version": settings.app_version,
            "database": collection_info,
            "memory": memory_summary,
            "model": settings.openai_model_name,
            "vector_size": settings.qdrant_vector_size
        }
    except Exception as e:
        logger.error("Error getting app info", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve application information")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    metrics_collector.record_error("http_error")
    logger.warning(
        "HTTP exception",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            error_code=str(exc.status_code),
            timestamp=time.time()
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    metrics_collector.record_error("general_error")
    logger.error(
        "Unhandled exception",
        error=str(exc),
        path=request.url.path,
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            error_code="500",
            timestamp=time.time()
        ).dict()
    )


# Add metrics recording middleware
@app.middleware("http")
async def record_metrics(request: Request, call_next):
    """Record request metrics."""
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    metrics_collector.record_request(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code,
        duration=duration
    )
    
    return response