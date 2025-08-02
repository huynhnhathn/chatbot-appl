import pytest
import asyncio
from unittest.mock import Mock, patch
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import QdrantManager
from app.chatbot import ChatbotEngine
from app.models import ChatRequest, ChatResponse
from config import settings


class TestQdrantManager:
    """Test Qdrant database manager."""
    
    @pytest.fixture
    def db_manager(self):
        """Create a test database manager."""
        with patch('app.database.QdrantClient'):
            return QdrantManager()
    
    def test_get_embedding(self, db_manager):
        """Test embedding generation."""
        text = "Hello, world!"
        embedding = db_manager.get_embedding(text)
        
        assert isinstance(embedding, list)
        assert len(embedding) == db_manager.vector_size
        assert all(isinstance(x, float) for x in embedding)
    
    def test_add_documents(self, db_manager):
        """Test adding documents."""
        documents = [
            {
                "content": "Test document 1",
                "metadata": {"source": "test"},
                "source": "test"
            }
        ]
        
        # Mock the client upsert method
        db_manager.client.upsert = Mock()
        
        db_manager.add_documents(documents)
        db_manager.client.upsert.assert_called_once()


class TestChatbotEngine:
    """Test chatbot engine."""
    
    @pytest.fixture
    def chatbot_engine(self):
        """Create a test chatbot engine."""
        with patch('app.chatbot.ChatOpenAI'):
            with patch('app.chatbot.db_manager'):
                return ChatbotEngine()
    
    @pytest.mark.asyncio
    async def test_generate_response(self, chatbot_engine):
        """Test response generation."""
        # Mock the chain response
        chatbot_engine.chain.ainvoke = Mock()
        chatbot_engine.chain.ainvoke.return_value = {"text": "Hello! How can I help you?"}
        
        # Mock the context retrieval
        chatbot_engine._get_context = Mock()
        chatbot_engine._get_context.return_value = "No relevant context found."
        
        # Mock the chat history formatting
        chatbot_engine._format_chat_history = Mock()
        chatbot_engine._format_chat_history.return_value = "No previous conversation."
        
        result = await chatbot_engine.generate_response("Hello", "test_user")
        
        assert isinstance(result, dict)
        assert "response" in result
        assert "response_time" in result
        assert "tokens_used" in result
        assert "cost" in result
        assert result["response"] == "Hello! How can I help you?"
    
    def test_add_to_knowledge_base(self, chatbot_engine):
        """Test adding to knowledge base."""
        # Mock the database manager
        chatbot_engine.db_manager.add_documents = Mock()
        
        result = chatbot_engine.add_to_knowledge_base(
            "Test content",
            {"category": "test"},
            "test_source"
        )
        
        assert result is True
        chatbot_engine.db_manager.add_documents.assert_called_once()


class TestModels:
    """Test Pydantic models."""
    
    def test_chat_request(self):
        """Test ChatRequest model."""
        request = ChatRequest(
            message="Hello, world!",
            user_id="test_user",
            session_id="test_session"
        )
        
        assert request.message == "Hello, world!"
        assert request.user_id == "test_user"
        assert request.session_id == "test_session"
    
    def test_chat_response(self):
        """Test ChatResponse model."""
        response = ChatResponse(
            response="Hello! How can I help you?",
            context_used=True,
            response_time=1.5,
            tokens_used=100,
            cost=0.002
        )
        
        assert response.response == "Hello! How can I help you?"
        assert response.context_used is True
        assert response.response_time == 1.5
        assert response.tokens_used == 100
        assert response.cost == 0.002


class TestConfiguration:
    """Test configuration settings."""
    
    def test_settings_loaded(self):
        """Test that settings are loaded correctly."""
        assert hasattr(settings, 'openai_model_name')
        assert hasattr(settings, 'qdrant_host')
        assert hasattr(settings, 'app_name')
        assert hasattr(settings, 'port')
    
    def test_default_values(self):
        """Test default configuration values."""
        assert settings.openai_model_name == "gpt-4"
        assert settings.qdrant_host == "localhost"
        assert settings.qdrant_port == 6333
        assert settings.port == 8000


if __name__ == "__main__":
    # Run basic tests
    pytest.main([__file__, "-v"])