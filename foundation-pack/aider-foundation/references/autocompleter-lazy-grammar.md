<!-- capsule-v2 -->
# Lazy completion grammar — how does a terminal REPL offer identifiers, files, and commands without paying for lexing upfront?

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** How do you make prompt-toolkit completion fast at keystroke zero yet identifier-aware over every open file, while mirroring the command registry's reflection rules?

## One-shot tokenize latch feeding backtick-paired words; command plane mirrors reflection
**Path/Symbol:** `aider/io.py`: `AutoCompleter.__init__` (:92-125), `tokenize` (:127-146), `get_command_completions` (:148-184), `get_completions` (:186-227).
**Signature:** `tokenize() -> None` (idempotent latch); `get_completions(document, complete_event) -> Iterator[Completion]`; `get_command_completions(document, complete_event, text, words) -> Iterator[Completion]`.
**Data Shape:** `self.words` is a SET of plain strings and `(token, f"\`{token}\`")` PAIRS; `fname_to_rel_fnames` maps basename→[rel paths] only when basename ≠ rel path; `command_completions` caches per-command candidate lists.

### Decisive source
```python
def tokenize(self):
    if self.tokenized:
        return
    self.tokenized = True                     # :128-130 ONE-SHOT latch — first keystroke pays
    for fname in self.all_fnames:
        try: content = open(fname, encoding=self.encoding).read()
        except (FileNotFoundError, UnicodeDecodeError, IsADirectoryError): continue  # :136 skip bad files
        ...
        tokens = list(lexer.get_tokens(content))
        self.words.update(
            (token[1], f"`{token[1]}`") for token in tokens if token[0] in Token.Name
        )                                     # :143-146 Name tokens stored as PAIRS inserting INTO backticks
```

```python
candidates = self.words                      # :206 LIVE set aliasing, not a copy
candidates.update(set(self.fname_to_rel_fnames))  # :207 folds basenames into self.words forever
...
if len(last_word) < 3: return                # :213 minimum 3 typed chars
if word_match.lower().startswith(last_word.lower()):
    completions.append((word_insert, -len(last_word), word_match))
    rel_fnames = self.fname_to_rel_fnames.get(word_match, [])   # :221 basename → every rel path
```

**Flow:** init seeds `words` with addable+chat rel paths and builds the basename index; the FIRST completion keystroke triggers `tokenize()`, which pygments-lexes every chat and read-only file once — per-file failures (missing/undecodable/directory, lexer crash) are swallowed individually so one hostile file never disables completion. Name-class tokens enter as `(word, backticked-word)` pairs so identifiers complete INTO chat fences. Dispatch: trailing space stops completion entirely (:194-196); text starting "/" routes to command completions where `CommandCompletionException` falls THROUGH to word completion (:198-204); word completion requires ≥3 chars, case-insensitive prefix match, expands basename hits to every matching rel path, and yields sorted for determinism. The command plane mirrors commands.py reflection: first word prefix-matches command names (sorted yield); later words resolve via `commands.matching_commands` exact-over-prefix, hand control entirely to `completions_raw_<cmd>` when defined, else cache `completions_<cmd>()` candidates once per command and substring-filter.
**Invariant:** lexing cost is paid exactly once per session regardless of how many completions run; no unreadable file can break the completer; command completion semantics can never drift from the reflected command table because they call the same resolver.
**Quirks to decide deliberately:** (a) `candidates = self.words` binds the LIVE set and `.update()` permanently folds basename keys into it on the first word-completion keystroke (:206-207) — stateful, harmless here, but not a local copy; (b) one basename hit appends every matching rel path per tuple (:221-224), so shared prefixes yield duplicate entries — sorted() gives determinism, not dedup. Graph note: `search_graph("get_completions")` returns a TIE — Commands.get_completions :266-274 and AutoCompleter.get_completions :186-227 both rank −24.08 (total 2); cite the io.py symbol explicitly.
**Probe:** `.venv/bin/python -m pytest tests/basic/test_io.py -k autocompleter -q` (within the executed subset: **7 passed**) incl. the pair assertion that `hello` completes as `` (`hello`, `\`hello\``) ``; anchors :128-146/:206-213 byte-checked this run.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "aider", qualified_name: "aider.aider.io.AutoCompleter.tokenize" });
// serves io.py :127-146 with the latch + pair inserts byte-exact
await mcp.codebase_memory.search_graph({ project: "aider", query: "get_completions", limit: 5 });
// total:2 TIE — aider.aider.commands.Commands.get_completions 266-274 / aider.aider.io.AutoCompleter.get_completions 186-227
```

## Verdict
Adopt the one-shot tokenize latch, per-file failure swallowing, backtick-pair insertion, and command-plane reuse of the reflection resolver. Adapt lexer choice and the ≥3-char gate to your host shell. Omit nothing silently: make the live-set fold-in and duplicate-basename expansion deliberate decisions in your reimplementation (copy or fix, but know you chose).
