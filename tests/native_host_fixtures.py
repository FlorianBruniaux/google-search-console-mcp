"""Normalized, local CLI events for subprocess adapters; no vendor invocation."""


def codex_completed_events_source():
    return '''
import json, sys
from pathlib import Path
if '--output-last-message' in sys.argv:
    text = Path(sys.argv[sys.argv.index('--output-last-message') + 1]).read_text()
    for event in [
        {'type': 'thread.started', 'thread_id': 'fixture-thread'},
        {'type': 'turn.started'},
        {'type': 'item.completed', 'item': {'id': 'final', 'type': 'agent_message', 'text': text}},
        {'type': 'turn.completed', 'usage': {'input_tokens': 1, 'output_tokens': 1}},
    ]:
        print(json.dumps(event))
'''
