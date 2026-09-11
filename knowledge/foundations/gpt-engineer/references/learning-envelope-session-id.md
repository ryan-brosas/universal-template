<!-- capsule-v2 -->
# learning-envelope-session-id — How is a session serialized into a Learning envelope, and how stable is its session identity?

**Source:** gpt-engineer MIT `main@a90fcd543eedcc0ff2c34561bc0785d2ba83c47e`; Codebase Memory `gpt-engineer`. **Question:** What exactly goes into the Learning payload, and where does the session id come from?

## Envelope seam
**Path/Symbol:** `gpt_engineer/applications/cli/learning.py:Learning` (:73-109) + `extract_learning` (:237-276) + `get_session` (:279-301).
**Signature:** `extract_learning(prompt: Prompt, model: str, temperature: float, config: Tuple[str,...], memory: DiskMemory, review: Review) -> Learning`; `get_session() -> str`.
**Data Shape:** Learning(prompt:str-json, model:str, temperature:float, config:str-json, logs:str, session:str, review:Optional[Review], timestamp:str=utcnow-isoformat, version:str="0.3"); @dataclass_json decorated for `.to_dict()/.to_json()`.

### Decisive source
```python
return Learning(
    prompt=prompt.to_json(),          # Prompt.to_dict -> json.dumps (core/prompt.py:36-44)
    model=model,
    temperature=temperature,
    config=json.dumps(config),        # the (code_gen_fn.__name__, execution_fn.__name__) tuple
    session=get_session(),
    logs=memory.to_json(),            # WHOLE DiskMemory serialized into one string field
    review=review,
)
...
path = Path(tempfile.gettempdir()) / "gpt_engineer_user_id.txt"
try:
    if path.exists():
        user_id = path.read_text()
    else:
        # random uuid:
        user_id = str(random.randint(0, 2**32))   # NOT a uuid — a bare int in range [0, 2^32)
        path.write_text(user_id)
    return user_id
except IOError:
    return "ephemeral_" + str(random.randint(0, 2**32))
```

**Flow:** generate tail → collect_and_send_human_review → human_review_input returns Review → extract_learning snapshots prompt JSON + mode-config tuple + ENTIRE memory dir as JSON + session id → Learning stamped with UTC timestamp and schema version "0.3" at construction.
**Invariant:** (1) `logs=memory.to_json()` embeds ALL project memory (chats/history) — this is why the sender needs a 32KB truncation ladder; any new big field re-triggers it. (2) Session identity is a random int persisted in the OS TEMP DIR, shared across projects and surviving until temp cleanup; the inline comment says "uuid" but the value is `random.randint(0, 2**32)` — do not "fix" silently, analytics continuity depends on the shape. (3) IOError on the temp file degrades to an `"ephemeral_"`-prefixed throwaway id rather than failing the run. (4) timestamp/version are DEFAULT_FACTORY fields — they fill only when omitted; extract_learning omits both deliberately. (5) config records WHICH step functions ran (function-name tuple from main :545), not their code.
**Probe:** `tests/applications/cli/test_learning.py` — test_extract_learning :78-98 asserts isinstance(result, Learning) with mocked `memory.to_json`; test_get_session :101-110 mocks Path+random to pin `"42"` round-trip.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "gpt-engineer", query: "extract_learning get_session Learning dataclass_json timestamp version", limit: 10 });
```

## Verdict
Adopt the envelope fields + whole-memory snapshot rationale + tempdir-persistent session id with ephemeral fallback; adapt serialization lib (dataclasses_json is host-swappable); omit the hardcoded schema version only if you bump it consciously. Direct tests are shallow here (isinstance + mocked id) — deeper behavior rests on source reads, recorded honestly.
