#!/usr/bin/env python3
"""
Semantic search interface for openclaw-memory
Implements progressive disclosure pattern
"""

from typing import List, Dict, Optional
from datetime import datetime
from .database import MemoryDatabase
from .embeddings import EmbeddingGenerator

class MemorySearch:
    """Search interface with progressive disclosure"""
    
    def __init__(self, db: MemoryDatabase = None, embedding_gen: EmbeddingGenerator = None):
        self.db = db or MemoryDatabase()
        self.embedding_gen = embedding_gen or EmbeddingGenerator(backend="local")
    
    def search_index(self, query: str, limit: int = 10, 
                     date_range: tuple = None,
                     event_type: str = None) -> List[Dict]:
        """
        Step 1: Search index (compact results)
        Returns ~50-100 tokens per result
        
        Args:
            query: Search query
            limit: Max results
            date_range: (start_ts, end_ts) optional
            event_type: Filter by event type
        
        Returns:
            List of compact result dicts with id, title, date, score
        """
        # Generate query embedding
        query_embedding = self.embedding_gen.generate(query)
        
        # Get all indexed chunks (TODO: optimize with vector index)
        cursor = self.db.conn.execute("""
            SELECT c.id, c.content, c.timestamp, c.event_type, c.source_file, e.vector
            FROM memory_chunks c
            JOIN embeddings e ON c.id = e.chunk_id
            WHERE 1=1
                AND (? IS NULL OR c.event_type = ?)
                AND (? IS NULL OR c.timestamp >= ?)
                AND (? IS NULL OR c.timestamp <= ?)
        """, (
            event_type, event_type,
            date_range[0] if date_range else None, date_range[0] if date_range else None,
            date_range[1] if date_range else None, date_range[1] if date_range else None
        ))
        
        # Calculate similarities
        results = []
        for row in cursor.fetchall():
            chunk_embedding = self.embedding_gen.decode_vector(row['vector'])
            similarity = self.embedding_gen.cosine_similarity(query_embedding, chunk_embedding)
            
            # Extract title (first line or first 50 chars)
            content = row['content']
            title = content.split('\n')[0][:50]
            if len(title) < len(content.split('\n')[0]):
                title += "..."
            
            results.append({
                'id': row['id'],
                'title': title,
                'date': datetime.fromtimestamp(row['timestamp']).strftime('%Y-%m-%d'),
                'type': row['event_type'],
                'source': row['source_file'],
                'relevance': round(similarity, 4)
            })
        
        # Sort by relevance and return top results
        results.sort(key=lambda x: x['relevance'], reverse=True)
        self.db.log_search(query, len(results[:limit]))
        
        return results[:limit]
    
    def get_timeline(self, memory_id: int, window_hours: int = 5) -> List[Dict]:
        """
        Step 2: Get timeline context around a memory
        
        Args:
            memory_id: Memory chunk ID
            window_hours: Hours before/after to include
        
        Returns:
            List of memories with basic info
        """
        chunks = self.db.get_timeline(memory_id, window=window_hours)
        
        return [{
            'id': c['id'],
            'timestamp': datetime.fromtimestamp(c['timestamp']).strftime('%Y-%m-%d %H:%M'),
            'type': c['event_type'],
            'preview': c['content'][:100] + ('...' if len(c['content']) > 100 else '')
        } for c in chunks]
    
    def get_memories(self, ids: List[int]) -> List[Dict]:
        """
        Step 3: Get full memory details (batch)
        
        Args:
            ids: List of memory IDs
        
        Returns:
            List of full memory dicts
        """
        chunks = self.db.get_chunks(ids)
        
        return [{
            'id': c['id'],
            'source': c['source_file'],
            'lines': f"{c['line_start']}-{c['line_end']}" if c['line_start'] else None,
            'content': c['content'],
            'timestamp': datetime.fromtimestamp(c['timestamp']).strftime('%Y-%m-%d %H:%M:%S'),
            'type': c['event_type'],
            'metadata': c['metadata']
        } for c in chunks]
    
    def search_fulltext(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Fallback: Simple text search if no embeddings
        """
        chunks = self.db.search_fulltext(query, limit)
        
        return [{
            'id': c['id'],
            'source': c['source_file'],
            'preview': c['content'][:200] + ('...' if len(c['content']) > 200 else ''),
            'date': datetime.fromtimestamp(c['timestamp']).strftime('%Y-%m-%d'),
            'type': c['event_type']
        } for c in chunks]


if __name__ == "__main__":
    import sys
    
    # Test search
    search = MemorySearch()
    
    if len(sys.argv) > 1:
        query = ' '.join(sys.argv[1:])
        print(f"Searching for: {query}")
        print()
        
        # Try semantic search
        results = search.search_index(query, limit=5)
        
        if results:
            print(f"Found {len(results)} results:")
            for i, r in enumerate(results, 1):
                print(f"\n{i}. [{r['relevance']:.3f}] {r['title']}")
                print(f"   Date: {r['date']} | Type: {r['type']} | ID: {r['id']}")
        else:
            # Fallback to text search
            print("No semantic results, trying text search...")
            results = search.search_fulltext(query)
            for i, r in enumerate(results, 1):
                print(f"\n{i}. {r['preview']}")
                print(f"   Date: {r['date']} | Source: {r['source']}")
    else:
        stats = search.db.get_stats()
        print("Memory Search Ready")
        print(f"  Total chunks: {stats['total_chunks']}")
        print(f"  Indexed chunks: {stats['indexed_chunks']}")
        print(f"  Coverage: {stats['indexed_chunks'] / max(stats['total_chunks'], 1) * 100:.1f}%")
        print()
        print("Usage: python3 search.py <query>")
