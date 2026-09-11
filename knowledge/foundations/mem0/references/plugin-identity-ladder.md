<!-- capsule-v2 -->
# Identity resolution ladder — where does an API key come from when env vars don't reach the process?

**Source:** mem0 Apache-2.0 `main@7e096155`; Codebase Memory `mem0`. **Question:** how do you resolve credentials/user identity for a tool spawned by a GUI app that never inherited the user's shell profile?

## Connected graph-selected seam
**Path/Symbol:** `integrations/mem0-plugin/scripts/_identity.py`: `resolve_api_key` (:55-68), `_extract_key_from_shell_profiles` (:26-52), `resolve_user_id` (:71-75), `resolve_config` ImportError fallback (:78-91).
**Signature:** `resolve_api_key() -> str`; `_extract_key_from_shell_profiles() -> str`; `resolve_user_id() -> str`.
**Data Shape:** key ladder of four rungs returning "" when all miss; profile scan over [`.zshrc`, `.bashrc`, `.zprofile`, `.bash_profile`, `.profile`].

### Decisive source
```python
pattern = re.compile(r'^\s*(?:export\s+)?MEM0_API_KEY=(.+)$')
...
value = m.group(1).strip()
value = re.sub(r'#.*$', '', value).strip()   # strip inline comments
value = value.strip("\"'")
if value and not value.startswith("$"):      # reject $VAR indirection
    return value
```

**Flow:** MEM0_API_KEY env → CLAUDE_PLUGIN_OPTION_API_KEY (userConfig) → CLAUDE_PLUGIN_OPTION_MEM0_API_KEY (legacy) → first non-empty match in five shell profiles → "". User id: MEM0_USER_ID → $USER → "default".
**Invariant:** first non-empty wins; a matched value that is empty after comment/quote stripping does NOT win (scan continues); $-prefixed values are treated as unresolved indirection and skipped; OSError on one profile file never aborts the walk.
**Probe:** `cd $REFERENCE_ROOT/mem0 && .venv/bin/python -m pytest integrations/mem0-plugin/tests/test_write_path.py -q -k resolve` plus deterministic grep `grep -n 'startswith("\$")' integrations/mem0-plugin/scripts/_identity.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_code({ project: "mem0", pattern: "_extract_key_from_shell_profiles" });
```

## Verdict
Adopt the ladder + the three regex guards (comment, quote, $indirection) for any GUI-spawned helper needing shell-profile secrets; adapt profile list/env names to host; omit mem0-specific option names.
