#!/usr/bin/env python3
"""
Database layer for openclaw-memory semantic search
Uses SQLite with vector extension
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

class MemoryDatabase:
    """SQLite database with vector search for memory persistence"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            workspace = Path.home() / ".openclaw" / "workspace"
            db_path = workspace / "memory" / "memory.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        self._init_db()
    
    def _init_db(self):
        """Initialize database with schema"""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        
        # Create tables
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS memory_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_file TEXT NOT NULL,
                line_start INTEGER,
                line_end INTEGER,
                content TEXT NOT NULL,
                embedding_model TEXT,
                timestamp INTEGER NOT NULL,
                event_type TEXT,
                metadata TEXT
            );
            
            CREATE INDEX IF NOT EXISTS idx_timestamp ON memory_chunks(timestamp);
            CREATE INDEX IF NOT EXISTS idx_source ON memory_chunks(source_file);
            CREATE INDEX IF NOT EXISTS idx_type ON memory_chunks(event_type);
            
            -- Embeddings stored separately for flexibility
            CREATE TABLE IF NOT EXISTS embeddings (
                chunk_id INTEGER PRIMARY KEY,
                vector BLOB NOT NULL,
                model TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (chunk_id) REFERENCES memory_chunks(id)
            );
            
            -- Search history for learning
            CREATE TABLE IF NOT EXISTS search_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                result_count INTEGER,
                timestamp INTEGER NOT NULL
            );
        """)
        self.conn.commit()
    
    def add_chunk(self, 
                  source_file: str,
                  content: str,
                  timestamp: int,
                  line_start: int = None,
                  line_end: int = None,
                  event_type: str = None,
                  metadata: dict = None) -> int:
        """Add a memory chunk"""
        cursor = self.conn.execute("""
            INSERT INTO memory_chunks 
            (source_file, content, timestamp, line_start, line_end, event_type, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            source_file,
            content,
            timestamp,
            line_start,
            line_end,
            event_type,
            json.dumps(metadata) if metadata else None
        ))
        self.conn.commit()
        return cursor.lastrowid
    
    def add_embedding(self, chunk_id: int, vector: bytes, model: str):
        """Store embedding for a chunk"""
        timestamp = int(datetime.now().timestamp())
        self.conn.execute("""
            INSERT OR REPLACE INTO embeddings (chunk_id, vector, model, created_at)
            VALUES (?, ?, ?, ?)
        """, (chunk_id, vector, model, timestamp))
        self.conn.commit()
    
    def get_chunk(self, chunk_id: int) -> Optional[Dict]:
        """Retrieve a single chunk by ID"""
        cursor = self.conn.execute("""
            SELECT * FROM memory_chunks WHERE id = ?
        """, (chunk_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    def get_chunks(self, chunk_ids: List[int]) -> List[Dict]:
        """Batch retrieve chunks"""
        if not chunk_ids:
            return []
        
        placeholders = ','.join('?' * len(chunk_ids))
        cursor = self.conn.execute(f"""
            SELECT * FROM memory_chunks WHERE id IN ({placeholders})
        """, chunk_ids)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_unindexed_chunks(self) -> List[Dict]:
        """Get chunks without embeddings"""
        cursor = self.conn.execute("""
            SELECT c.* FROM memory_chunks c
            LEFT JOIN embeddings e ON c.id = e.chunk_id
            WHERE e.chunk_id IS NULL
        """)
        return [dict(row) for row in cursor.fetchall()]
    
    def search_fulltext(self, query: str, limit: int = 10) -> List[Dict]:
        """Simple text search (fallback if no embeddings)"""
        cursor = self.conn.execute("""
            SELECT * FROM memory_chunks
            WHERE content LIKE ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (f'%{query}%', limit))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_timeline(self, chunk_id: int, window: int = 5) -> List[Dict]:
        """Get chunks around a specific chunk for temporal context"""
        chunk = self.get_chunk(chunk_id)
        if not chunk:
            return []
        
        timestamp = chunk['timestamp']
        cursor = self.conn.execute("""
            SELECT * FROM memory_chunks
            WHERE timestamp BETWEEN ? AND ?
            ORDER BY timestamp ASC
        """, (timestamp - window * 3600, timestamp + window * 3600))
        return [dict(row) for row in cursor.fetchall()]
    
    def log_search(self, query: str, result_count: int):
        """Log search for analytics"""
        timestamp = int(datetime.now().timestamp())
        self.conn.execute("""
            INSERT INTO search_log (query, result_count, timestamp)
            VALUES (?, ?, ?)
        """, (query, result_count, timestamp))
        self.conn.commit()
    
    def get_stats(self) -> Dict:
        """Get database statistics"""
        cursor = self.conn.execute("""
            SELECT 
                COUNT(*) as total_chunks,
                COUNT(DISTINCT source_file) as total_files,
                MIN(timestamp) as earliest,
                MAX(timestamp) as latest
            FROM memory_chunks
        """)
        stats = dict(cursor.fetchone())
        
        cursor = self.conn.execute("""
            SELECT COUNT(*) as indexed_chunks FROM embeddings
        """)
        stats['indexed_chunks'] = cursor.fetchone()[0]
        
        return stats
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


if __name__ == "__main__":
    # Test database
    import sys
    
    db = MemoryDatabase()
    
    if len(sys.argv) > 1 and sys.argv[1] == "stats":
        stats = db.get_stats()
        print("Memory Database Statistics:")
        print(f"  Total chunks: {stats['total_chunks']}")
        print(f"  Indexed chunks: {stats['indexed_chunks']}")
        print(f"  Total files: {stats['total_files']}")
        if stats['earliest']:
            from datetime import datetime
            earliest = datetime.fromtimestamp(stats['earliest'])
            latest = datetime.fromtimestamp(stats['latest'])
            print(f"  Date range: {earliest.date()} to {latest.date()}")
    else:
        print("Database initialized successfully")
        print(f"Location: {db.db_path}")
        print("\nUsage:")
        print("  python3 database.py stats    # Show statistics")
    
    db.close()
