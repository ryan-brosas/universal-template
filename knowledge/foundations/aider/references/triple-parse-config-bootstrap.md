<!-- capsule-v2 -->
# Triple-parse config bootstrap — CWD→git-root→home ladder with wrong-repo restart and .env reparse

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider` (7,507n/19,923e, head==pin). **Question:** How does a CLI agent bootstrap configuration when its config-file search order depends on the git root, which itself can't be known until args are parsed?

## Parse three times; the git root is only trustworthy after pass two
**Path/Symbol:** `aider/main.py`: `get_git_root()` (:60), `guessed_wrong_repo(io, git_root, fnames, git_dname)` (:69), `main()` config ladder (:464-504), recursion (:716-720), `check_config_files_for_yes(config_files)` (:43), `load_dotenv_files(git_root, dotenv_fname, encoding)` (:361).
**Signature:** `main(argv=None, input=None, output=None, force_git_root=None, return_coder=False)` — recursion is `main(argv, input, output, right_repo_root, return_coder=return_coder)` carrying ONLY the corrected root.
**Data Shape:** default_config_files built as [CWD/.aider.conf.yml resolved, <git_root>/.aider.conf.yml (deduped), ~/.aider.conf.yml] = highest-to-lowest precedence for argparse defaults.

### Decisive source
```python
parser = get_parser(default_config_files, git_root)
args, unknown = parser.parse_known_args(argv)
...   # AttributeError containing bool/object/has/no/attribute/strip
      # ⇒ check_config_files_for_yes() → friendly "replace 'yes:' with
      #   'yes-always:'" message instead of a stack trace
default_config_files.reverse()          # now lowest-first for display
parser = get_parser(default_config_files, git_root)   # rebuild parser
args, unknown = parser.parse_known_args(argv)
loaded_dotenvs = load_dotenv_files(git_root, args.env_file, args.encoding)
args = parser.parse_args(argv)          # third parse: env-derived argv wins
...
if args.git and not force_git_root and git is not None:
    right_repo_root = guessed_wrong_repo(io, git_root, fnames, git_dname)
    if right_repo_root:
        analytics.event("exit", reason="Recursing with correct repo")
        return main(argv, input, output, right_repo_root, return_coder=return_coder)
```

**Flow:** guess root from cwd → parse #1 (tolerant, catches the malformed-YAML `yes:` AttributeError signature) → reverse list & rebuild parser so later files don't shadow earlier ones in help/default computation → load `.env` files discovered from parsed args (`~/.aider/oauth-keys.env` is INSERTED AT POSITION 0 of the search list, overriding repo/homedir values; each file loads with `override=True`) → parse #2 strict (env may define new flags) → after files are classified, `guessed_wrong_repo` builds a throwaway `GitRepo` to find the TRUE root and recurses whole-`main` if it differs.
**Invariant:** config precedence is stable regardless of which directory you launch from, because the final parser is rebuilt once the real git root is known; every exit path inside the bootstrap emits an analytics `"exit"` event with a machine-readable reason before returning.
**Probe:** deterministic anchors: `grep -c 'parse_known_args' aider/main.py` → 2; `grep -cF 'Recursing with correct repo' aider/main.py` → 1. Direct tests: `tests/basic/test_main.py` drives main() end-to-end; `tests/basic/test_sanity_check_repo.py` covers the sibling sanity gate.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "generate_search_path_list", limit: 3 });
// rank-1: aider.aider.main.generate_search_path_list aider/main.py 305-332
```

## Verdict
Adopt the triple-parse + wrong-repo-restart pattern verbatim for any CLI whose config search order depends on discovered state; adapt the `yes:` typo sniff (very aider-specific) and the analytics event vocabulary. The porter's classic mistake — parsing once and trusting the cwd-derived git root — silently mis-locates `.aider.conf.yml`, history files, and `.env` in subdirectories of monorepos.
