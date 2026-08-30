<!-- capsule-v2 -->
# Env persistence — why is the settings menu a .env editor instead of a config store?

**Source:** Scout MIT `main@171503bf`; Codebase Memory `Scout`. **Question:** How does a stateless script make runtime settings changes survive restarts without a config file format?

## Boot-time .env absorb + line-preserving write-back
**Path/Symbol:** `scout.py:.env loader` (:44-51), `_update_env(key, value)` (:143-159); consumers `settings_menu` (:927-1017).
**Signature:** `_update_env(key: str, value: str) -> None` (writes file AND mutates `os.environ`).
**Data Shape:** `.env` next to `scout.py`; flat `KEY=VALUE` lines, `#` comments allowed, values never quoted; keys: `LINKEDIN_COOKIE`, `HUNTER_API_KEY`, `SCOUT_PROXY`, `SCOUT_PROXY_FILE`, `SCOUT_FREE_PROXY`, `SCOUT_DELAY_MIN/MAX`.

### Decisive source
```python
# boot: setdefault — real environment ALWAYS wins over the file
for _line in _f:
    if _line and not _line.startswith('#') and '=' in _line:
        _key, _, _val = _line.partition('=')
        os.environ.setdefault(_key.strip(), _val.strip())

# write-back: rewrite whole file preserving unrelated lines & comments
for line in f:
    if line.strip().startswith(key + '='):
        lines.append(f'{key}={value}\n')
        found = True
    else:
        lines.append(line)
if not found:
    lines.append(f'{key}={value}\n')
with open(env_path, 'w') as f:
    f.writelines(lines)
os.environ[key] = value               # live process updated too
```

**Flow:** every settings action calls `_update_env`, which rewrites the file in place (only lines whose stripped prefix matches `key=` are replaced; unknown keys append at EOF) and mirrors into `os.environ` so the change takes effect immediately without restart. Removal writes empty strings *and* pops the env var (:989-993).
**Invariant:** dual-write is mandatory — updating only the file loses the current session, updating only the environ loses persistence. `setdefault` semantics at boot mean an exported shell variable overrides the file, so users can temporarily override without editing. Matching is on `key + '='` after strip, so `SCOUT_DELAY_MIN` cannot collide with a hypothetical `SCOUT_DELAY_MIN_X`.
**Probe:** no direct test (zero-test repo). Deterministic probe: `grep -n "_update_env\|setdefault" scout.py` pins :51, :143-159, and all TEN call sites (:930-1016); `python - <<'EOF'` harness can round-trip `_update_env` against a temp dir since it takes no global state beyond cwd-relative path.
**Coverage caveat:** `_update_env` resolves `.env` relative to `Path(__file__).parent`, not cwd — porters who switch to cwd-relative break the "run from anywhere" property.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Scout", query: "_update_env env_file settings", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt setdefault-at-boot + full-file-rewrite write-back + same-call environ mirror as the minimal durable-config primitive; adapt key names and add atomic temp-rename if crash-safety matters (Scout accepts the tiny corruption window); omit the rich settings UI around it. Note the deliberate plain-text storage of the LinkedIn session cookie — a security trade-off a porter should consciously revisit.
