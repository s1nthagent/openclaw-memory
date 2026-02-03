# Phase 2: Semantic Search - Implementation Plan

**Goal:** Enable semantic search across memory files for intelligent context retrieval

**Date:** 2026-02-03  
**Status:** Planning → Building

---

## Architecture Decision

### Option 1: SQLite-vec (CHOSEN)
- ✅ Single-file database (no separate service)
- ✅ Already have SQLite dependency
- ✅ Fast, proven, simple
- ✅ 100% local (privacy)
- ❌ Limited to SQLite ecosystem

### Option 2: ChromaDB
- ✅ Better for large-scale
- ✅ More features (metadata filtering)
- ❌ Requires separate service
- ❌ More complex setup
- ❌ Heavier dependencies

**Decision:** Start with SQLite-vec for Phase 2. Can migrate to Chroma in Phase 3 if needed.

---

## Implementation Plan

### 1. Database Schema
```sql
CREATE TABLE memory_embeddings (
    id INTEGER PRIMARY KEY,
    source_file TEXT NOT NULL,
    line_start INTEGER,
    line_end INTEGER,
    content TEXT NOT NULL,
    embedding BLOB NOT NULL,
    timestamp INTEGER,
    event_type TEXT,
    metadata JSON
);

CREATE INDEX idx_timestamp ON memory_embeddings(timestamp);
CREATE INDEX idx_source ON memory_embeddings(source_file);
```

### 2. Embedding Generation
Use OpenAI/Anthropic/local embedding model:
- Chunk daily notes into semantic blocks (paragraphs/sections)
- Generate embeddings for each chunk
- Store with metadata (file, date, type)

### 3. Search Implementation
**Progressive Disclosure Pattern (from claude-mem):**

**Step 1: Index Search** (~50-100 tokens/result)
```python
def search_index(query: str, limit: int = 10):
    """Returns compact results with IDs"""
    embedding = generate_embedding(query)
    results = vector_search(embedding, limit)
    return [
        {
            'id': r.id,
            'title': extract_title(r.content),
            'date': r.timestamp,
            'relevance': r.score
        } for r in results
    ]
```

**Step 2: Timeline View**
```python
def get_timeline(memory_id: int, context_window: int = 5):
    """Get surrounding memories for temporal context"""
    return get_memories_around(memory_id, window=context_window)
```

**Step 3: Full Details**
```python
def get_memories(ids: List[int]):
    """Batch fetch full content"""
    return fetch_full_content(ids)
```

### 4. MCP Tools (OpenClaw Integration)
Create skill that exposes:
- `memory_search(query, date_range, type_filter)` → index
- `memory_timeline(memory_id, window)` → timeline
- `memory_get(ids)` → full content

### 5. Auto-Indexing
Update `memory-consolidate.py`:
```python
def index_new_memories():
    """Called after consolidation"""
    new_entries = get_unindexed_memories()
    for entry in new_entries:
        embedding = generate_embedding(entry.content)
        store_embedding(entry, embedding)
```

---

## Dependencies

```
# requirements.txt
sqlite-vec>=0.1.0
sentence-transformers>=2.2.0  # For local embeddings
openai>=1.0.0  # If using OpenAI embeddings (optional)
```

---

## Files to Create

```
openclaw-memory/
├── scripts/
│   ├── index-memories.py          # Generate embeddings
│   ├── search-memories.py         # Search interface
│   └── memory-consolidate.py      # (update with auto-index)
├── lib/
│   ├── embeddings.py              # Embedding generation
│   ├── search.py                  # Vector search
│   └── database.py                # SQLite-vec ops
├── docs/
│   ├── PHASE2_PLAN.md             # This file
│   └── SEARCH_API.md              # Search tool docs
└── skills/
    └── memory-search/
        ├── SKILL.md
        └── search.py
```

---

## Testing Strategy

1. Index last 7 days of memory files
2. Test search queries:
   - "What did I build yesterday?"
   - "When did we discuss memory systems?"
   - "Show me all decisions about Squad S1NTH"
3. Verify progressive disclosure saves tokens
4. Benchmark search speed (<100ms)

---

## Success Criteria

- ✅ Can search memories semantically
- ✅ Results ranked by relevance
- ✅ Progressive disclosure working (10x token savings)
- ✅ Auto-indexing on consolidation
- ✅ MCP skill for OpenClaw integration
- ✅ Documentation complete

---

## Timeline

- Database setup: 30 min
- Embedding pipeline: 1 hour
- Search implementation: 1 hour
- MCP skill: 30 min
- Testing: 30 min
- **Total: ~3-4 hours**

---

## Starting Now

Building database layer first, then embeddings, then search.
