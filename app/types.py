"""
Type definitions and stubs for external libraries.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

if TYPE_CHECKING:
    # Qdrant types
    from qdrant_client.models import CollectionInfo, PointStruct, ScoredPoint
    
    # LangChain types
    from langchain.schema import BaseMessage
    
    # FastAPI types
    from fastapi import Request
    
    # Custom type aliases
    EmbeddingVector = List[float]
    DocumentPayload = Dict[str, Any]
    SearchResult = Dict[str, Union[str, float, Dict[str, Any]]]
    CollectionInfoDict = Dict[str, Union[str, int, float]]
    
else:
    # Runtime type aliases (when TYPE_CHECKING is False)
    CollectionInfo = Any
    PointStruct = Any
    ScoredPoint = Any
    BaseMessage = Any
    Request = Any
    EmbeddingVector = List[float]
    DocumentPayload = Dict[str, Any]
    SearchResult = Dict[str, Union[str, float, Dict[str, Any]]]
    CollectionInfoDict = Dict[str, Union[str, int, float]]

# Type guards for runtime checking
def is_collection_info(obj: Any) -> bool:
    """Check if object is a CollectionInfo instance."""
    return hasattr(obj, 'name') and hasattr(obj, 'config') and hasattr(obj, 'points_count')

def is_scored_point(obj: Any) -> bool:
    """Check if object is a ScoredPoint instance."""
    return hasattr(obj, 'id') and hasattr(obj, 'score') and hasattr(obj, 'payload')

def is_point_struct(obj: Any) -> bool:
    """Check if object is a PointStruct instance."""
    return hasattr(obj, 'id') and hasattr(obj, 'vector') and hasattr(obj, 'payload')