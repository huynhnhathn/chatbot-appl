from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from langchain.callbacks import get_openai_callback
from typing import List, Dict, Any, Optional
import json
import time
from app.database import db_manager
from app.logger import get_logger
from config import settings

logger = get_logger(__name__)


class ChatbotEngine:
    """Main chatbot engine using LangChain and OpenAI."""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openai_model_name,
            temperature=settings.openai_temperature,
            max_tokens=settings.openai_max_tokens,
            openai_api_key=settings.openai_api_key
        )
        
        # Conversation memory
        self.memory = ConversationBufferWindowMemory(
            k=10,  # Keep last 10 exchanges
            return_messages=True
        )
        
        # System prompt template
        self.system_prompt = """You are a helpful and knowledgeable AI assistant. You have access to a knowledge base that you can search to provide accurate and relevant information.

When responding to user queries:
1. Use the provided context from the knowledge base when available
2. Be concise but comprehensive
3. If you don't have relevant information in the knowledge base, rely on your general knowledge
4. Always be helpful and professional
5. If you're unsure about something, acknowledge the limitation

Context from knowledge base:
{context}

Current conversation:
{chat_history}

User: {user_input}
Assistant:"""

        self.prompt = ChatPromptTemplate.from_template(self.system_prompt)
        
        self.chain = LLMChain(
            llm=self.llm,
            prompt=self.prompt,
            verbose=settings.debug
        )
    
    def _get_context(self, query: str, max_results: int = 3) -> str:
        """Retrieve relevant context from the vector database."""
        try:
            similar_docs = db_manager.search_similar(
                query=query,
                limit=max_results,
                score_threshold=0.7
            )
            
            if not similar_docs:
                return "No relevant context found in knowledge base."
            
            context_parts = []
            for doc in similar_docs:
                context_parts.append(f"Source: {doc['source']}\nContent: {doc['content']}\n")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error("Error retrieving context", error=str(e))
            return "Error retrieving context from knowledge base."
    
    def _format_chat_history(self) -> str:
        """Format chat history for the prompt."""
        try:
            messages = self.memory.chat_memory.messages
            if not messages:
                return "No previous conversation."
            
            formatted_history = []
            for message in messages[-6:]:  # Last 6 messages
                if isinstance(message, HumanMessage):
                    formatted_history.append(f"User: {message.content}")
                elif isinstance(message, AIMessage):
                    formatted_history.append(f"Assistant: {message.content}")
            
            return "\n".join(formatted_history)
            
        except Exception as e:
            logger.error("Error formatting chat history", error=str(e))
            return "Error formatting conversation history."
    
    async def generate_response(self, user_input: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate a response to user input."""
        start_time = time.time()
        
        try:
            # Get relevant context
            context = self._get_context(user_input)
            
            # Format chat history
            chat_history = self._format_chat_history()
            
            # Prepare input for the chain
            chain_input = {
                "context": context,
                "chat_history": chat_history,
                "user_input": user_input
            }
            
            # Generate response with OpenAI callback for monitoring
            with get_openai_callback() as cb:
                response = await self.chain.ainvoke(chain_input)
                
                # Log usage metrics
                logger.info(
                    "OpenAI API usage",
                    total_tokens=cb.total_tokens,
                    prompt_tokens=cb.prompt_tokens,
                    completion_tokens=cb.completion_tokens,
                    total_cost=cb.total_cost,
                    user_id=user_id
                )
            
            response_time = time.time() - start_time
            
            # Get the response text
            response_text = response["text"].strip()
            
            # Manually add messages to memory
            self.memory.chat_memory.add_user_message(user_input)
            self.memory.chat_memory.add_ai_message(response_text)
            
            # Prepare response
            result = {
                "response": response_text,
                "context_used": context != "No relevant context found in knowledge base.",
                "response_time": round(response_time, 3),
                "tokens_used": cb.total_tokens if 'cb' in locals() else 0,
                "cost": cb.total_cost if 'cb' in locals() else 0.0
            }
            
            logger.info(
                "Response generated successfully",
                response_time=result["response_time"],
                tokens_used=result["tokens_used"],
                context_used=result["context_used"],
                user_id=user_id
            )
            
            return result
            
        except Exception as e:
            response_time = time.time() - start_time
            logger.error(
                "Error generating response",
                error=str(e),
                response_time=response_time,
                user_id=user_id
            )
            
            return {
                "response": "I apologize, but I encountered an error while processing your request. Please try again.",
                "error": str(e),
                "response_time": round(response_time, 3),
                "context_used": False,
                "tokens_used": 0,
                "cost": 0.0
            }
    
    def add_to_knowledge_base(self, content: str, metadata: Optional[Dict[str, Any]] = None, source: str = "user_input") -> bool:
        """Add content to the knowledge base."""
        try:
            document = {
                "content": content,
                "metadata": metadata or {},
                "source": source,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            db_manager.add_documents([document])
            logger.info("Content added to knowledge base", source=source)
            return True
            
        except Exception as e:
            logger.error("Error adding to knowledge base", error=str(e))
            return False
    
    def clear_memory(self) -> None:
        """Clear the conversation memory."""
        try:
            self.memory.clear()
            logger.info("Conversation memory cleared")
        except Exception as e:
            logger.error("Error clearing memory", error=str(e))
    
    def get_memory_summary(self) -> Dict[str, Any]:
        """Get a summary of the current memory state."""
        try:
            messages = self.memory.chat_memory.messages
            return {
                "message_count": len(messages),
                "has_memory": len(messages) > 0,
                "last_message_time": time.time() if messages else None
            }
        except Exception as e:
            logger.error("Error getting memory summary", error=str(e))
            return {"message_count": 0, "has_memory": False, "last_message_time": None}


# Global chatbot engine instance
chatbot_engine = ChatbotEngine()