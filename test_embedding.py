#!/usr/bin/env python3
"""
Test script to verify embedding generation works correctly.
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.append(str(Path(__file__).parent))

def test_embedding_generation():
    """Test embedding generation with different tensor types."""
    
    try:
        from app.database import QdrantManager
        import torch
        import numpy as np
        
        print("Testing embedding generation...")
        
        # Create a mock QdrantManager (without actual database connection)
        class MockQdrantManager(QdrantManager):
            def __init__(self):
                # Skip database initialization for testing
                pass
            
            def _ensure_collection_exists(self):
                # Skip for testing
                pass
        
        # Create manager instance
        manager = MockQdrantManager()
        
        # Test text
        test_text = "Hello, this is a test sentence for embedding generation."
        
        print(f"Testing with text: '{test_text}'")
        
        # Generate embedding
        embedding = manager.get_embedding(test_text)
        
        print(f"✓ Successfully generated embedding")
        print(f"  - Type: {type(embedding)}")
        print(f"  - Length: {len(embedding)}")
        print(f"  - First 5 values: {embedding[:5]}")
        
        # Verify it's a list of floats
        if isinstance(embedding, list) and all(isinstance(x, (int, float)) for x in embedding):
            print("✓ Embedding is valid list of numbers")
            return True
        else:
            print("✗ Embedding is not a valid list of numbers")
            return False
            
    except Exception as e:
        print(f"✗ Error during embedding test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_embedding_generation()
    if success:
        print("\n✓ Embedding generation test passed!")
    else:
        print("\n✗ Embedding generation test failed!")
        sys.exit(1)