# English request check

The same fourteen intent categories were submitted in English through the running editor API, resetting state for every case. Result:11/14 passed; no image generation. Cases and raw API results: english-cases.json and english-results.json.

Failures:
- Black shirt. → unchanged navy
- Restore the shirt color to the original image. → unchanged navy instead of original
- Make it like before. → accepted as unchanged rather than asking for clarification

Standard changes, synonyms, additions, removals, preservation, negation, correction, multiple edits and rejection of unsupported hair editing passed in these cases. This is a small diagnostic set, not general language accuracy. The earlier Korean14-case run preceded removal of a faulty deletion override; the English run followed that fix. Therefore10/14 versus11/14 is not evidence that English is better. Short instructions, original-state restoration and ambiguous history references remain problematic in both sets.
