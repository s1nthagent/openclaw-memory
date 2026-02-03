#!/usr/bin/env python3
"""
Memory Consolidation System - Phase 1
Automates MEMORY.md updates from daily notes

Usage:
  python3 memory-consolidate.py              # Interactive mode
  python3 memory-consolidate.py --auto       # Auto-consolidate (for cron)
  python3 memory-consolidate.py --dry-run    # Preview changes
"""

import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE = Path.home() / ".openclaw" / "workspace"
MEMORY_FILE = WORKSPACE / "MEMORY.md"
MEMORY_DIR = WORKSPACE / "memory"

def read_file(path):
    """Safe file read"""
    try:
        return path.read_text()
    except FileNotFoundError:
        return ""

def write_file(path, content):
    """Safe file write"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)

def get_recent_daily_notes(days=7):
    """Get daily notes from last N days"""
    notes = []
    for i in range(days):
        date = datetime.now() - timedelta(days=i)
        filename = f"{date.strftime('%Y-%m-%d')}.md"
        filepath = MEMORY_DIR / filename
        if filepath.exists():
            notes.append({
                'date': date.strftime('%Y-%m-%d'),
                'path': filepath,
                'content': read_file(filepath)
            })
    return notes

def extract_key_events(daily_notes):
    """Extract significant events from daily notes
    
    Looks for:
    - Lines starting with ## (headings)
    - Lines with ✅ or 🔥 or 🚀 (completed/important work)
    - Lines in decision/action sections
    """
    events = []
    for note in daily_notes:
        content = note['content']
        date = note['date']
        
        # Simple extraction - look for headings and checkmarks
        for line in content.split('\n'):
            line = line.strip()
            
            # Skip empty or very short lines
            if not line or len(line) < 10:
                continue
                
            # Capture headings
            if line.startswith('##'):
                events.append({
                    'date': date,
                    'type': 'heading',
                    'text': line.replace('##', '').strip()
                })
            
            # Capture completed items
            elif '✅' in line or '🔥' in line or '🚀' in line:
                events.append({
                    'date': date,
                    'type': 'completion',
                    'text': line
                })
            
            # Capture decisions
            elif 'Decision:' in line or 'DECISION:' in line:
                events.append({
                    'date': date,
                    'type': 'decision',
                    'text': line
                })
    
    return events

def format_recent_history(events):
    """Format events into RECENT HISTORY section"""
    if not events:
        return ""
    
    # Group by date
    by_date = {}
    for event in events:
        date = event['date']
        if date not in by_date:
            by_date[date] = []
        by_date[date].append(event)
    
    # Format
    lines = []
    for date in sorted(by_date.keys(), reverse=True):
        lines.append(f"\n### {date}")
        for event in by_date[date]:
            lines.append(f"- {event['text']}")
    
    return '\n'.join(lines)

def update_memory_file(dry_run=False):
    """Update MEMORY.md with consolidated events"""
    
    # Get recent notes
    daily_notes = get_recent_daily_notes(days=7)
    if not daily_notes:
        print("No recent daily notes found")
        return False
    
    # Extract events
    events = extract_key_events(daily_notes)
    if not events:
        print("No significant events found")
        return False
    
    # Read current MEMORY.md
    current_memory = read_file(MEMORY_FILE)
    
    # Generate new RECENT HISTORY section
    new_history = format_recent_history(events)
    
    # Find and replace RECENT HISTORY section
    # This is naive - assumes section exists and is marked
    # Real version would be more robust
    
    if dry_run:
        print("DRY RUN - Would update MEMORY.md with:")
        print(new_history)
        return True
    
    # For now, just append to a consolidation log
    # Real version would intelligently merge into MEMORY.md
    log_file = MEMORY_DIR / "consolidation.log"
    timestamp = datetime.now().isoformat()
    log_entry = f"\n\n## Consolidation Run: {timestamp}\n{new_history}\n"
    
    with open(log_file, 'a') as f:
        f.write(log_entry)
    
    print(f"Consolidated {len(events)} events from {len(daily_notes)} daily notes")
    print(f"Logged to {log_file}")
    return True

if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    auto = "--auto" in sys.argv
    
    if auto or dry_run:
        update_memory_file(dry_run=dry_run)
    else:
        # Interactive mode
        print("Memory Consolidation Tool")
        print("=========================")
        print()
        response = input("Consolidate recent daily notes into MEMORY.md? [y/N] ")
        if response.lower() == 'y':
            update_memory_file(dry_run=False)
        else:
            print("Cancelled")
