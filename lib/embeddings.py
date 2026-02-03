#!/usr/bin/env python3
"""
Embedding generation for semantic search
Supports multiple backends: OpenAI, sentence-transformers (local)
"""

import os
import struct
from typing import List, Optional
from pathlib import Path

class EmbeddingGenerator:
    """Generate embeddings for semantic search"""
    
    def __init__(self, backend: str = "local", model: str = None):
        """
        Initialize embedding generator
        
        Args:
            backend: 'openai' or 'local' (sentence-transformers)
            model: Model name (optional, uses defaults)
        """
        self.backend = backend
        
        if backend == "openai":
            try:
                import openai
                self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                self.model = model or "text-embedding-3-small"
                self.dimension = 1536
            except ImportError:
                raise ImportError("Install openai: pip install openai")
        
        elif backend == "local":
            try:
                from sentence_transformers import SentenceTransformer
                self.model = model or "all-MiniLM-L6-v2"
                self.encoder = SentenceTransformer(self.model)
                self.dimension = self.encoder.get_sentence_embedding_dimension()
            except ImportError:
                raise ImportError("Install sentence-transformers: pip install sentence-transformers")
        
        else:
            raise ValueError(f"Unknown backend: {backend}")
    
    def generate(self, text: str) -> List[float]:
        """Generate embedding for text"""
        if self.backend == "openai":
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )
            return response.data[0].embedding
        
        elif self.backend == "local":
            return self.encoder.encode(text).tolist()
    
    def generate_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        if self.backend == "openai":
            response = self.client.embeddings.create(
                model=self.model,
                input=texts
            )
            return [item.embedding for item in response.data]
        
        elif self.backend == "local":
            embeddings = self.encoder.encode(texts)
            return [emb.tolist() for emb in embeddings]
    
    def encode_vector(self, embedding: List[float]) -> bytes:
        """Encode embedding as binary for storage"""
        return struct.pack(f'{len(embedding)}f', *embedding)
    
    def decode_vector(self, data: bytes) -> List[float]:
        """Decode binary embedding"""
        count = len(data) // 4
        return list(struct.unpack(f'{count}f', data))
    
    @staticmethod
    def cosine_similarity(a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        import math
        
        dot_product = sum(x * y for x, y in zip(a, b))
        magnitude_a = math.sqrt(sum(x * x for x in a))
        magnitude_b = math.sqrt(sum(y * y for y in b))
        
        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0
        
        return dot_product / (magnitude_a * magnitude_b)


def chunk_text(text: str, max_chars: int = 500, overlap: int = 50) -> List[str]:
    """
    Split text into overlapping chunks for embedding
    
    Args:
        text: Text to chunk
        max_chars: Maximum characters per chunk
        overlap: Characters to overlap between chunks
    
    Returns:
        List of text chunks
    """
    if len(text) <= max_chars:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + max_chars
        
        # Try to break at paragraph
        if end < len(text):
            newline_pos = text.rfind('\n\n', start, end)
            if newline_pos != -1 and newline_pos > start + max_chars // 2:
                end = newline_pos
            else:
                # Break at sentence
                period_pos = text.rfind('. ', start, end)
                if period_pos != -1 and period_pos > start + max_chars // 2:
                    end = period_pos + 1
        
        chunks.append(text[start:end].strip())
        start = end - overlap
    
    return chunks


if __name__ == "__main__":
    import sys
    
    # Test embedding generation
    backend = sys.argv[1] if len(sys.argv) > 1 else "local"
    
    print(f"Testing embedding generator (backend: {backend})")
    
    try:
        gen = EmbeddingGenerator(backend=backend)
        print(f"✅ Initialized with model: {gen.model}")
        print(f"   Dimension: {gen.dimension}")
        
        # Test single embedding
        test_text = "This is a test memory entry for semantic search."
        embedding = gen.generate(test_text)
        print(f"\n✅ Generated embedding for test text")
        print(f"   Vector length: {len(embedding)}")
        print(f"   Sample values: {embedding[:5]}")
        
        # Test encoding/decoding
        encoded = gen.encode_vector(embedding)
        decoded = gen.decode_vector(encoded)
        print(f"\n✅ Encode/decode working")
        print(f"   Encoded size: {len(encoded)} bytes")
        print(f"   Decoded matches: {embedding[:5] == decoded[:5]}")
        
        # Test similarity
        text2 = "Another memory about searching through data."
        embedding2 = gen.generate(text2)
        similarity = gen.cosine_similarity(embedding, embedding2)
        print(f"\n✅ Similarity calculation working")
        print(f"   Similarity score: {similarity:.4f}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
