from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, 
    VectorParams, 
    PointStruct, 
    Filter, 
    FieldCondition, 
    Range, 
    MatchValue
)
from qdrant_client.http import models
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
from app.logger import get_logger
from config import settings

logger = get_logger(__name__)


class QdrantManager:
    """Manages Qdrant vector database operations."""
    
    def __init__(self):
        self.client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port
        )
        self.collection_name = settings.qdrant_collection_name
        self.vector_size = settings.qdrant_vector_size
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self._ensure_collection_exists()
    
    def _ensure_collection_exists(self) -> None:
        """Ensure the collection exists, create if it doesn't."""
        try:
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                logger.info("Creating new collection", collection_name=self.collection_name)
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info("Collection created successfully")
            else:
                logger.info("Collection already exists", collection_name=self.collection_name)
                
        except Exception as e:
            logger.error("Error ensuring collection exists", error=str(e))
            raise
    
    def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for given text."""
        try:
            embedding = self.embedding_model.encode(text)
            return embedding.tolist()
        except Exception as e:
            logger.error("Error generating embedding", error=str(e), text=text[:100])
            raise
    
    def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """Add documents to the vector database."""
        try:
            points = []
            for doc in documents:
                embedding = self.get_embedding(doc['content'])
                point = PointStruct(
                    id=doc.get('id', hash(doc['content'])),
                    vector=embedding,
                    payload={
                        'content': doc['content'],
                        'metadata': doc.get('metadata', {}),
                        'source': doc.get('source', 'unknown'),
                        'timestamp': doc.get('timestamp', '')
                    }
                )
                points.append(point)
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            logger.info("Documents added successfully", count=len(documents))
            
        except Exception as e:
            logger.error("Error adding documents", error=str(e))
            raise
    
    def search_similar(self, query: str, limit: int = 5, score_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Search for similar documents based on query."""
        try:
            query_embedding = self.get_embedding(query)
            
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=score_threshold
            )
            
            results = []
            for result in search_result:
                results.append({
                    'id': result.id,
                    'score': result.score,
                    'content': result.payload.get('content', ''),
                    'metadata': result.payload.get('metadata', {}),
                    'source': result.payload.get('source', ''),
                    'timestamp': result.payload.get('timestamp', '')
                })
            
            logger.info("Search completed", query_length=len(query), results_count=len(results))
            return results
            
        except Exception as e:
            logger.error("Error searching documents", error=str(e), query=query[:100])
            raise
    
    def delete_documents(self, filter_conditions: Optional[Dict[str, Any]] = None) -> None:
        """Delete documents based on filter conditions."""
        try:
            if filter_conditions:
                # Build filter from conditions
                filter_obj = Filter(
                    must=[
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value)
                        ) for key, value in filter_conditions.items()
                    ]
                )
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=filter_obj
                )
            else:
                # Delete all documents
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=models.PointIdsList(
                        points=[]
                    )
                )
            
            logger.info("Documents deleted successfully")
            
        except Exception as e:
            logger.error("Error deleting documents", error=str(e))
            raise
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection."""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            return {
                'name': collection_info.name,
                'vector_size': collection_info.config.params.vectors.size,
                'distance': collection_info.config.params.vectors.distance,
                'points_count': collection_info.points_count
            }
        except Exception as e:
            logger.error("Error getting collection info", error=str(e))
            raise
    
    def health_check(self) -> bool:
        """Check if the database is healthy."""
        try:
            self.client.get_collections()
            return True
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return False


# Global database manager instance
db_manager = QdrantManager()