# Recall project session evidence

Answer one historical question using the smallest sufficient slice of session
evidence.

## Authority

- Raw session JSONL, current-session events, or an explicitly supplied
  transcript establish what happened.
- Current source, tests, requirements, compiler output, and runtime behavior
  establish what is true now.
- Summaries, memories, embeddings, indexes, and reflections are projections,
  not independent authority.

## Method

1. Resolve the active project and the named question.
2. Use one nearest sufficient raw source: the current session, project-scoped
   session JSONL, or an explicitly supplied transcript. A recall provider may
   locate events only when its result retains provenance to them.
3. Search the active project only by default. Cross-project or global recall
   requires an explicit request.
4. Return the minimum relevant evidence with available session identifiers,
   timestamps, event or tool-call ranges, and source paths.
5. Verify material claims about the current code against current source and
   tests.
6. Stop when the question is answered or available evidence is exhausted.

## Output

    Question:
    Scope:
    Relevant evidence:
    Current-source check:
    Answer:
    Coverage and uncertainty:

## Rules

- Read-only: create or update no memory, note, skill, foundation, index, or
  cache.
- Do not dump entire session logs.
- Do not invent missing evidence.
- Redact secret values and omit unrelated private content.
- Hindsight, OpenViking, Fabric recall, and similar systems are optional
  adapters, never independent authority.

Request:

$ARGUMENTS
