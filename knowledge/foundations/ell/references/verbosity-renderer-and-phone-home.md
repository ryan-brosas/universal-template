<!-- capsule-v2 -->
# verbosity renderer and phone-home — how do I render streaming LLM output in a terminal without breaking on width, and what ships with it?

**Source:** ell MIT `main@9d129846203e75efeb4e5cddd3fb1c164dc0b243`; Codebase Memory `ext-ell`. **Question:** What does the verbose logging plane actually do at call time — including the outbound network request a porter must know about?

## box renderer + stream chunk wrapper + version ping
**Path/Symbol:** `src/ell/util/verbosity.py` (`model_usage_logger_pre` :96-119, `model_usage_logger_post_start/intermediate/end` :122-235, `compute_color` :60-66, `check_version_and_log` :38-56); zero-dep progress twin `src/ell/util/tqdm.py:tqdm` (:9-34).
**Signature:** `model_usage_logger_post_intermediate(n: int = 1)` — contextmanager yielding `log_stream_chunk(stream_chunk: str, is_refusal: bool = False)`.
**Data Shape:** colors derived from `md5(lmp.__name__) % len(ELL_COLORS)` via lru_cache; roles pinned system=cyan/user=green/assistant=yellow; ASCII box drawn to terminal width (default 80).

### Decisive source
```python
# verbosity.py:143-163 — manual wrap accounting for streamed text
def log_stream_chunk(stream_chunk: str , is_refusal: bool = False):
    nonlocal chars_printed
    if stream_chunk:
        lines = stream_chunk.split('\n')
        for i, line in enumerate(lines):
            if chars_printed + len(line) > terminal_width - 6:
                print()
                if i == 0:
                    print(subsequent_prefix, end='')
                    chars_printed = len(prefix)
                else:
                    print(subsequent_prefix, end='')
                    chars_printed = len(subsequent_prefix)
                print(line.lstrip(), end='')
            else:
                print(line, end='')
            chars_printed += len(line)
```

```python
# verbosity.py:40-43 — THE PHONE-HOME (fires once per process on first logged call)
response = requests.get("https://version.ell.so/ell-ai/pypi", timeout=0.15)
if response.status_code == 200:
    latest_version = response.text.strip()
    if latest_version != ell.__version__:
        ...print update banner...
```

**Flow:** pre-call renders an argument preview and the prompt box (images rendered as ASCII via plot_ascii); during the provider call the contextmanager receives stream chunks and wraps manually with a running char counter (chunk boundaries never align with lines); post-call closes the box. The first logged invocation also fires the one-shot version check guarded by a lock + module flag. `tqdm.py` is a 36-line dependency-free progress bar used by evaluations with adaptive skip-rate (`self.skip`) so high-frequency loops don't drown stderr.
**Invariant:** rendering is gated on `should_log = not exempt_from_tracking and config.verbose` at the complex.py call site — verbose logging and tracking share one gate; and the version ping is fire-once-per-process, non-blocking-ish (150ms timeout), silently swallowed on RequestException.
**Probe:** deterministic anchors from repo root: `grep -n 'version.ell.so' src/ell/util/verbosity.py` → line 41 exactly; `grep -c 'terminal_width - 2' src/ell/util/verbosity.py` == 4 (box edges). No direct unit test at pin (rendering is stdout-coupled — coverage caveat recorded honestly).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ell", query: "stream chunks index", limit: 5, fields: ["signature", "name", "file"] });
// adjacent provider seam that feeds log_stream_chunk; verbosity itself is stdout-coupled (BM25 thin)
```

## Verdict
Adopt the char-counter stream wrapping for any terminal LLM renderer. Adapt colors/box glyphs freely. OMIT the version ping from any port unless you intend to operate the same telemetry — this capsule exists precisely so porters don't ship a surprise outbound call.
