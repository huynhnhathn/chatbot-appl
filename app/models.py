from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    role: MessageRole
    content: str
    timestamp: Optional[datetime] = None
    
    @validator('timestamp', pre=True, always=True)
    def set_timestamp(cls, v):
        return v or datetime.utcnow()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    user_id: Optional[str] = Field(None, description="User identifier for tracking")
    session_id: Optional[str] = Field(None, description="Session identifier")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class ChatResponse(BaseModel):
    response: str = Field(..., description="AI assistant response")
    context_used: bool = Field(..., description="Whether knowledge base context was used")
    response_time: float = Field(..., description="Response generation time in seconds")
    tokens_used: int = Field(..., description="Number of tokens used")
    cost: float = Field(..., description="Cost of the API call")
    error: Optional[str] = Field(None, description="Error message if any")
    session_id: Optional[str] = Field(None, description="Session identifier")


class KnowledgeBaseRequest(BaseModel):
    content: str = Field(..., min_length=1, description="Content to add to knowledge base")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    source: str = Field("user_input", description="Source of the content")


class KnowledgeBaseResponse(BaseModel):
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    document_id: Optional[str] = Field(None, description="Document identifier if created")


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search query")
    limit: int = Field(5, ge=1, le=20, description="Maximum number of results")
    score_threshold: float = Field(0.7, ge=0.0, le=1.0, description="Minimum similarity score")


class SearchResult(BaseModel):
    id: str = Field(..., description="Document identifier")
    score: float = Field(..., description="Similarity score")
    content: str = Field(..., description="Document content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Document metadata")
    source: str = Field(..., description="Document source")
    timestamp: str = Field(..., description="Document timestamp")


class SearchResponse(BaseModel):
    results: List[SearchResult] = Field(..., description="Search results")
    total_results: int = Field(..., description="Total number of results")
    query: str = Field(..., description="Original search query")


class HealthCheckResponse(BaseModel):
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Check timestamp")
    version: str = Field(..., description="Application version")
    database_healthy: bool = Field(..., description="Database health status")
    openai_healthy: bool = Field(..., description="OpenAI API health status")
    uptime: float = Field(..., description="Application uptime in seconds")


class MetricsResponse(BaseModel):
    total_requests: int = Field(..., description="Total number of requests")
    successful_requests: int = Field(..., description="Number of successful requests")
    failed_requests: int = Field(..., description="Number of failed requests")
    average_response_time: float = Field(..., description="Average response time in seconds")
    total_tokens_used: int = Field(..., description="Total tokens used")
    total_cost: float = Field(..., description="Total cost incurred")
    active_sessions: int = Field(..., description="Number of active sessions")


class ConversationHistory(BaseModel):
    session_id: str = Field(..., description="Session identifier")
    messages: List[ChatMessage] = Field(..., description="Conversation messages")
    created_at: datetime = Field(..., description="Session creation time")
    last_activity: datetime = Field(..., description="Last activity time")
    message_count: int = Field(..., description="Total number of messages")


class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")