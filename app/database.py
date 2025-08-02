from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, 
    VectorParams, 
    PointStruct, 
    Filter, 
    FieldCondition, 
    Range, 
    MatchValue,
    CollectionInfo
)
from qdrant_client.http import models
from typing import List, Dict, Any, Optional, Tuple, Union
import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from app.logger import get_logger
from app.types import CollectionInfoDict, SearchResult, is_collection_info, is_scored_point
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
            
            # Handle potential None values and type issues
            collection_names = []
            if hasattr(collections, 'collections') and collections.collections:
                for col in collections.collections:
                    try:
                        name = getattr(col, 'name', None)
                        if name:
                            collection_names.append(name)
                    except AttributeError:
                        continue
            
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
            
            # Convert to numpy array first, then to list
            if isinstance(embedding, torch.Tensor):
                embedding = embedding.detach().cpu().numpy()
            elif isinstance(embedding, list) and len(embedding) > 0 and isinstance(embedding[0], torch.Tensor):
                # Handle list of tensors
                embedding = torch.stack(embedding).detach().cpu().numpy()
            
            # Ensure it's a numpy array
            if not isinstance(embedding, np.ndarray):
                embedding = np.array(embedding)
            
            # Convert to list
            return embedding.tolist()
                
        except Exception as e:
            logger.error("Error generating embedding", error=str(e), text=text[:100])
            raise
    
    def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """Add documents to the vector database."""
        try:
            points = []
            for doc in documents:
                if not doc or 'content' not in doc:
                    logger.warning("Skipping document with missing content")
                    continue
                    
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
    
    def search_similar(self, query: str, limit: int = 5, score_threshold: float = 0.7) -> List[SearchResult]:
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
                # Use type guard to ensure result is a ScoredPoint
                if not is_scored_point(result):
                    logger.warning("Skipping invalid search result")
                    continue
                    
                # Handle case where payload might be None
                payload: Dict[str, Any] = result.payload or {}
                results.append({
                    'id': result.id,
                    'score': result.score,
                    'content': payload.get('content', ''),
                    'metadata': payload.get('metadata', {}),
                    'source': payload.get('source', ''),
                    'timestamp': payload.get('timestamp', '')
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
    
    def get_collection_info(self) -> CollectionInfoDict:
        """Get information about the collection."""
        try:
            collection_info: CollectionInfo = self.client.get_collection(self.collection_name)
            
            # Use type guard to ensure collection_info is valid
            if not is_collection_info(collection_info):
                logger.warning("Invalid collection info returned from Qdrant")
                raise ValueError("Invalid collection info")
            
            # Handle potential None values and type issues
            try:
                name = getattr(collection_info, 'name', self.collection_name)
                vector_size = getattr(collection_info.config.params.vectors, 'size', self.vector_size)
                distance = getattr(collection_info.config.params.vectors, 'distance', 'Cosine')
                points_count = getattr(collection_info, 'points_count', 0)
            except AttributeError:
                # Fallback values if attributes don't exist
                name = self.collection_name
                vector_size = self.vector_size
                distance = 'Cosine'
                points_count = 0
            
            return {
                'name': name,
                'vector_size': vector_size,
                'distance': distance,
                'points_count': points_count
            }
        except Exception as e:
            logger.error("Error getting collection info", error=str(e))
            # Return default values on error
            return {
                'name': self.collection_name,
                'vector_size': self.vector_size,
                'distance': 'Cosine',
                'points_count': 0
            }
    
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