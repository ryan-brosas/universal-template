<!-- capsule-v2 -->
# Slash-command plane — how do markdown `/commands` expand into agent goals without dropping user arguments?

**Source:** pipeshub-ai Apache-2.0 `main@c28d133…`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** How does a client-side markdown command file (`/name args`) get loaded and expanded into the text that BECOMES an agent's goal — and where does the args text go when the template has no placeholder?

## Flat-file command loader with OPTIONAL frontmatter
**Path/Symbol:** `backend/python/app/agent_loop_lib/commands/loader.py:_FRONTMATTER_RE/parse_command_md/load_commands_from_dir` (:26 / :29 / :53) + `commands/base.py:Command` + `commands/registry.py:CommandRegistry.render` (:32).
**Signature:** `_FRONTMATTER_RE = re.compile(r"\A---[ \t]*\n(.*?)^---[ \t]*\n?(.*)\Z", re.DOTALL | re.MULTILINE)`; `parse_command_md(content: str, name: str) -> Command`; `render(self, name: str, args: str = "") -> str`.
**Data Shape:** One `.md` file IS one command named after its basename — unlike SKILL.md there is NO directory-per-command layout and frontmatter is fully optional (a bare file is a valid command). `Command(name, description="", argument_hint=None, body)`.

### Decisive source
```python
# `^---` (not a bundled "\n---") so a genuinely empty frontmatter block
# ("---\n---\n") parses correctly — the newline ending the opening line
# would otherwise have to double as both "end of content" and "start of the
# closing delimiter's preceding newline", which a single consumed character
# can't do.
_FRONTMATTER_RE = re.compile(r"\A---[ \t]*\n(.*?)^---[ \t]*\n?(.*)\Z", re.DOTALL | re.MULTILINE)
...
def render(self, name: str, args: str = "") -> str:
    command = self.resolve(name)
    if ARGUMENTS_PLACEHOLDER in command.body:          # "$ARGUMENTS"
        return command.body.replace(ARGUMENTS_PLACEHOLDER, args)
    if args:
        return f"{command.body}\n\n{args}"             # never silently drop args
    return command.body
```

**Flow:** `load_commands_from_dir(root)` scans flat sorted `.md` files, skipping (log+continue, NEVER raise) unreadable/YAML-broken files to match the skills loader resilience story → `ControlPlane` scans command dirs once at start and holds a `CommandRegistry` (`control_plane.py:346`) → CLI `/name args` resolves and calls `render()`.
**Invariant:** (1) The frontmatter regex is `\A`-anchored with a MULTILINE closing `^---`: an unanchored or `\n---\Z` pattern mis-parses empty frontmatter blocks or bodies containing horizontal rules. (2) `$ARGUMENTS` substitution is replace-all; absence of the placeholder falls back to APPENDING args as a trailing paragraph — dropping typed args silently is the failure this exists to prevent. (3) Dir loading degrades per-file, never fails the batch.
**Probe:** `backend/python/tests/unit/agent_loop_lib/control_plane/test_control_plane_coverage.py::test_commands_dir_scanned_at_start` (:139–143 — empty dir yields `cp.commands.names() == []`, registry wired but unloaded); loader behavior additionally pinned by the skills-loader twin suites.
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-pipeshub-ai","query":"parse_command_md CommandRegistry render","detail":"ids","limit":5}'
```

## Verdict
Adopt one-file-one-command with optional frontmatter, the `\A`-anchored regex, per-file degrade-on-load, and append-not-drop argument fallback. Adapt `$ARGUMENTS` placeholder vocabulary and frontmatter keys (`description`, `argument-hint`) to your CLI grammar. Omit PipesHub's ControlPlane start-time scan wiring (host-specific lifecycle). Coverage caveat: the loader has no dedicated unit suite beyond the ControlPlane wiring test — probe the regex against `"---\n---\nbody"` before trusting a port.
