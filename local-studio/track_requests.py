"""Research CLI: read {requests: [...]} and return current state + edit prompt."""
import json
import sys
from request_state import StateExtractor, render_prompt

if __name__ == '__main__':
    payload = json.load(sys.stdin)
    requests = payload.get('requests')
    if not isinstance(requests, list) or not requests or any(
            not isinstance(request, str) or not request.strip() for request in requests):
        raise ValueError('Provide a nonempty list of request strings')
    state, ledger = StateExtractor().replay(requests)
    print(json.dumps({'state': state, 'prompt': render_prompt(state), 'ledger': ledger},
                     ensure_ascii=False, indent=2))
