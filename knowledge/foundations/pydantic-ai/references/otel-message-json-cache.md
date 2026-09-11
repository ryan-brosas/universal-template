<!-- capsule-v2 -->
# OTel message-JSON fragment cache: identity key + ABA guard + end-of-run staleness audit

## Source / Question
`pydantic_ai_slim/pydantic_ai/_instrumentation.py` (+ consumer `models/instrumented.py`) — How do you cache serialized fragments of a GROWING message history so each request costs O(new messages), without ever serving a fragment that doesn't describe the object it claims to? A porter will naively key a cache by content or by weak id and serve stale/wrong bytes.

## Path / Symbol
`pydantic_ai_slim/pydantic_ai/_instrumentation.py` — `CachedMessageJson` (90–104), `MessageJsonCache: TypeAlias = dict[int, CachedMessageJson]` (107–120), `message_json_fragment` (246–253), `has_stale_message_json` (256–281); consumers: `models/instrumented.py::_input_messages_json` (218–244, already covered by instrumented-model-wrapper capsule) and `capabilities/instrumentation.py::wrap_model_request/for_run`.

## Signature
```python
@dataclass(slots=True)
class CachedMessageJson:
    message: ModelMessage   # held ONLY to pin id(); never read
    parts: object           # the message's .parts LIST OBJECT at serialize time
    fragment: bytes         # serialized array minus outer [ ]

MessageJsonCache: TypeAlias = dict[int, CachedMessageJson]  # keyed by id(message)

def message_json_fragment(settings, message) -> bytes
def has_stale_message_json(settings, messages, cache) -> bool
```

## Data Shape
One entry per input message ever seen this run. Key = `id(message)` (object address). Guard token = the `.parts` list compared **by identity** (`entry.parts is message.parts`). Fragment = `safe_to_json(settings.messages_to_otel_messages([message]))[1:-1]` — comma-joined OTel `ChatMessage` objects WITHOUT enclosing brackets so N fragments concatenate into one JSON array (`b'[' + join + b']'` at the consumer). One `ModelMessage` may map to multiple spec messages (ModelRequest → system+user) or none.

## Decisive source
Three rules make this correct where a naive id-keyed cache is wrong:
1. **ABA protection**: the entry holds `message` itself so the cached message stays alive while cached — "a cache hit is therefore guaranteed to be for this very object, never for a new message that recycled a garbage-collected message's address (e.g. a `dataclasses.replace`d sibling sharing the same `parts` list)" (:95–98).
2. **Parts identity invalidation**: hit requires `entry.parts is message.parts`; reassigning `.parts` (the SUPPORTED mutation style, e.g. dynamic system prompt re-evaluation) misses and re-serializes (:100–102, instrumented.py `_input_messages_json`).
3. **Eviction on every request**: entries whose id is no longer in the current history are dropped, so "the cache (and the messages it keeps alive) stays bounded by the current history even when a history processor prunes or rebuilds messages" (:110–113).

## Flow / Invariant
Per request: for each history message → cache lookup by `id(message)` → valid iff entry exists AND `entry.parts is message.parts` → else serialize via `message_json_fragment` and store `(message, parts, fragment)` → evict ids absent from current history → emit `[fragment,…]`. Invariants a porter MUST keep: never mutate a history message's fields in place after it may have been serialized (build new objects or reassign `.parts`) — in-place mutation is exactly what the audit below catches; cache lives per-run (created fresh per run, discarded at run end) so keys can't leak across runs; serialization must go through `safe_to_json` (lone-surrogate tolerance).

**End-of-run staleness audit**: `has_stale_message_json` runs ONCE per run (in `Instrumentation.wrap_run`'s `finally`, only when result present): re-serialize each still-valid entry (`parts` identical) and compare BYTES; any mismatch → warn `MessageHistoryMutatedWarning` ("in-place mutation … may not match the messages actually sent"). Deliberately best-effort: a message mutated then dropped/rebuilt before run end produces no warning — closing that gap costs O(history²)/request or double serialization on eviction, the exact workloads the cache exists to remove (:266–271). Entries whose `parts` was reassigned are skipped — they'd have refreshed anyway.

## Probe (direct test)
`tests/models/test_instrumented.py`: `test_input_messages_json_matches_whole_history_with_and_without_cache` (:367), `test_has_stale_message_json_detection_boundaries` (:431 — asserts clean→uncached-skipped→in-place-mutation flagged→parts-reassignment NOT flagged), `test_instrumented_model_serializes_lone_surrogates_without_crashing` (:459), `test_safe_to_json_falls_back_on_lone_surrogates` (:477).

## Retrieve
`search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'CachedMessageJson MessageJsonCache has_stale_message_json'`

## Verdict
**Adopt** the three-rule contract (pin-the-object identity cache + parts-identity invalidation + per-request eviction) for ANY per-request serializer over an append-mostly history. **Adapt** the end-of-run byte-compare audit to your warning channel; skip it if your framework forbids user mutation of history outright.
