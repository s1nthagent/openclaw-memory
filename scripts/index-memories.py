#!/usr/bin/env python3
"""
Index daily memory files for semantic search
Processes unindexed memories and generates embeddings
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from database import MemoryDatabase
from embeddings import EmbeddingGenerator, chunk_text

def extract_events_from_file(filepath: Path) -> list:
    """
    Extract significant events from a daily note file
    Returns list of (content, event_type, line_start, line_end)
    """
    if not filepath.exists():
        return []
    
    content = filepath.read_text()
    events = []
    
    current_section = None
    section_start = 0
    section_lines = []
    
    for i, line in enumerate(content.split('\n'), 1):
        stripped = line.strip()
        
        # Detect section headings
        if stripped.startswith('##'):
            # Save previous section
            if section_lines:
                section_content = '\n'.join(section_lines)
                if len(section_content) > 50:  # Skip tiny sections
                    events.append({
                        'content': section_content,
                        'type': current_section or 'section',
                        'line_start': section_start,
                        'line_end': i - 1
                    })
            
            # Start new section
            current_section = stripped.replace('##', '').strip().lower()
            section_start = i
            section_lines = [line]
        else:
            section_lines.append(line)
    
    # Save last section
    if section_lines:
        section_content = '\n'.join(section_lines)
        if len(section_content) > 50:
            events.append({
                'content': section_content,
                'type': current_section or 'section',
                'line_start': section_start,
                'line_end': len(content.split('\n'))
            })
    
    return events

def index_file(db: MemoryDatabase, 
               embedding_gen: EmbeddingGenerator,
               filepath: Path,
               dry_run: bool = False) -> int:
    """
    Index a single file
    Returns number of chunks indexed
    """
    try:
        # Get file timestamp
        date_str = filepath.stem  # YYYY-MM-DD
        file_date = datetime.strptime(date_str, '%Y-%m-%d')
        timestamp = int(file_date.timestamp())
    except ValueError:
        print(f"⚠️  Skipping {filepath.name} (invalid date format)")
        return 0
    
    # Check if already indexed
    cursor = db.conn.execute("""
        SELECT COUNT(*) FROM memory_chunks WHERE source_file = ?
    """, (str(filepath),))
    
    if cursor.fetchone()[0] > 0:
        return 0  # Already indexed
    
    # Extract events
    events = extract_events_from_file(filepath)
    
    if not events:
        return 0
    
    print(f"📄 {filepath.name}: {len(events)} events")
    
    if dry_run:
        for e in events[:3]:  # Show first 3
            preview = e['content'][:100].replace('\n', ' ')
            print(f"   - {e['type']}: {preview}...")
        return len(events)
    
    # Add to database
    indexed = 0
    for event in events:
        # Add chunk
        chunk_id = db.add_chunk(
            source_file=str(filepath),
            content=event['content'],
            timestamp=timestamp,
            line_start=event.get('line_start'),
            line_end=event.get('line_end'),
            event_type=event.get('type')
        )
        
        # Generate and store embedding
        try:
            embedding = embedding_gen.generate(event['content'])
            encoded = embedding_gen.encode_vector(embedding)
            db.add_embedding(chunk_id, encoded, embedding_gen.model)
            indexed += 1
        except Exception as e:
            print(f"   ⚠️  Failed to generate embedding: {e}")
    
    return indexed

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Index memory files for semantic search")
    parser.add_argument('--dry-run', action='store_true', help="Show what would be indexed")
    parser.add_argument('--all', action='store_true', help="Re-index all files (default: only new)")
    parser.add_argument('--backend', default='local', choices=['local', 'openai'], 
                       help="Embedding backend")
    parser.add_argument('files', nargs='*', help="Specific files to index")
    
    args = parser.parse_args()
    
    # Initialize
    print("🧠 Memory Indexer")
    print("=" * 50)
    
    db = MemoryDatabase()
    
    try:
        embedding_gen = EmbeddingGenerator(backend=args.backend)
        print(f"✅ Embedding model: {embedding_gen.model}")
    except Exception as e:
        print(f"❌ Failed to initialize embeddings: {e}")
        print("\nInstall dependencies:")
        print("  pip install sentence-transformers  # for local")
        print("  pip install openai                 # for openai")
        sys.exit(1)
    
    print()
    
    # Get files to index
    workspace = Path.home() / ".openclaw" / "workspace" / "memory"
    
    if args.files:
        files = [Path(f) for f in args.files]
    else:
        files = sorted(workspace.glob("2026-*.md"))
    
    if not files:
        print("No memory files found")
        sys.exit(0)
    
    # Index files
    total_chunks = 0
    total_files = 0
    
    for filepath in files:
        if not filepath.exists():
            print(f"⚠️  File not found: {filepath}")
            continue
        
        chunks = index_file(db, embedding_gen, filepath, dry_run=args.dry_run)
        if chunks > 0:
            total_chunks += chunks
            total_files += 1
    
    # Summary
    print()
    print("=" * 50)
    if args.dry_run:
        print(f"Would index {total_chunks} chunks from {total_files} files")
    else:
        print(f"✅ Indexed {total_chunks} chunks from {total_files} files")
        
        stats = db.get_stats()
        print(f"\nDatabase stats:")
        print(f"  Total chunks: {stats['total_chunks']}")
        print(f"  Indexed: {stats['indexed_chunks']}")
        print(f"  Coverage: {stats['indexed_chunks'] / max(stats['total_chunks'], 1) * 100:.1f}%")
    
    db.close()

if __name__ == "__main__":
    main()
