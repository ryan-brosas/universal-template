<!-- capsule-v2 -->
# Skills self-installer — one SKILL.md fanned out to every assistant skill dir with CLI-first text sourcing

**Source:** browser-use MIT `main@85ddbfedf609`; Codebase Memory `browser-use`. **Question:** how does a Python package ship its own agent-readable instructions and install them into N different AI assistants' skill directories from one CLI verb?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/skills/install.py` (184 lines): `TARGET_DIR_BUILDERS` (:25-34), `_all_target_skill_paths` (:39-44), `_load_skill_text_from_browser_harness_cli` (:76-88), `_resolve_output_paths` (:126-135), `_validate_output_paths` (:138-148), `handle` (:151-184); text sources `skills/browser_use.py` (`skill_text`, `as_browser_use_skill`).
**Signature:** CLI `browser-use skill show|install [--target {8 assistants|all}] [--path] [--force(ignored)] [--no-install]`; installers are a dict of zero-arg path builders so targets stay data, not code.
**Data Shape:** target map: `~/.{agents,claude,codex,copilot,cursor,gemini,openclaw}/skills/browser-use/SKILL.md` + XDG `$XDG_CONFIG_HOME/opencode/skills/browser-use/SKILL.md`; `all` appends the legacy non-XDG opencode path with set-style dedupe.

### Decisive source
```python
TARGET_DIR_BUILDERS = {
    'agents': lambda: _home_skill_dir('agents'),
    'claude': lambda: _home_skill_dir('claude'),   # ~/.claude/skills/browser-use
    ...
    'opencode': lambda: _xdg_config_home() / 'opencode' / 'skills' / SKILL_NAME,
}

# TEXT SOURCE PREFERENCE: live harness CLI output > package-embedded fallback
def _load_skill_text_from_browser_harness_cli() -> str:
    exe = _browser_harness_executable()          # shutil.which -> ~/.local/bin probe
    if exe is None:
        return _load_skill_text_from_package()   # silent degrade to embedded skill_text()
    result = subprocess.run([exe, 'skill'], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f'Failed to read skill from `{exe} skill`: {error}')
    return as_browser_use_skill(result.stdout)   # wrap foreign text in the skill envelope

# PATH VALIDATION LADDER: reject dir-as-file; walk UP to first existing ancestor before mkdir
if output_path.exists() and output_path.is_dir():
    raise RuntimeError(f'{output_path} is a directory, expected a SKILL.md file path.')
ancestor = output_path.parent
while not ancestor.exists():
    if ancestor.parent == ancestor: break
    ancestor = ancestor.parent
if ancestor.exists() and not ancestor.is_dir():
    raise RuntimeError(f'{ancestor} is not a directory.')

for output_path in output_paths:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding='utf-8')
```

**Flow:** `install` -> resolve outputs (custom --path wins; dir vs SKILL.md file both accepted) -> validate ladder -> unless `--no-install`, require uv on PATH and `uv tool install --python 3.12 --upgrade --force browser-use` (self-upgrade before sourcing) -> load skill text via the preference chain -> write identical bytes to every resolved path with parents created -> print per-path confirmation. `show` prints the text only. Unknown subcommand falls through to help + rc 1.
**Invariant:** overwrite-by-default is the documented semantics (`--force` accepted but ignored); missing harness binary degrades SILENTLY to embedded text while a FAILING harness binary is a loud RuntimeError; uv absence aborts install with an actionable message rather than half-installing; all target files get byte-identical content in one pass.
**Probe:** from repo root, call `_resolve_output_paths('all', None)`, `_resolve_output_paths('claude', Path('/tmp/bu-x'))`, `_resolve_output_paths('x', Path('/tmp/bu-y/SKILL.md'))`, plus `_validate_output_paths` rejection of a directory-as-file using a real tmpdir (executed this pass; output in verification.md).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "skill install target paths assistant SKILL.md", file_pattern: "browser_use/skills/*", limit: 12 });
```

## Verdict
Adopt for any tool that wants its docs/behavior read by coding agents: keep targets as a dict-of-path-builders, prefer LIVE sourced text over embedded copies (with silent binary-missing / loud binary-broken degradation), and validate the full ancestor chain before mkdir. The ignored-`--force` compatibility shim shows how to evolve CLI flags without breaking scripts. Do not port the hardcoded uv/python-3.12 pin without an equivalent upgrade story.
