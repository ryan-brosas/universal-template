<!-- capsule-v2 -->
# Dev-launcher env namespacing + interpreter ladder — how does one repo root run many isolated instances without colliding in /tmp or leaking a bad BU_NAME into filenames?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** What must a dev-mode launcher set before importing the package so parallel checkouts never share sockets, tmp, or state?

## cksum-namespaced dirs + three-tier exec ladder
**Path/Symbol:** repo-root `browser-harness` bash script (:1-34, whole file); consumed by `src/browser_harness/paths.py` accessors and `src/browser_harness/_ipc.py` stem logic.
**Signature:** `DEV_ID = cksum(ROOT)` (first whitespace field of `printf '%s' "$ROOT" | cksum`); exports `BH_HOME`, `BH_RUNTIME_DIR`, `BH_TMP_DIR` (+ `*_SHARED=1`) only when unset; then `exec` tier 1 `$ROOT/.venv/bin/python -m browser_harness.run` → tier 2 `uv --directory "$ROOT" run python -m browser_harness.run` → tier 3 `PYTHONPATH="$ROOT/src"` + plain `python3 -m browser_harness.run`.
**Data Shape:** `BH_HOME="${BH_HOME:-$ROOT/.browser-harness-dev}"`; `BH_RUNTIME_DIR="/tmp/bh-dev-$DEV_ID/runtime"` (SHARED default 1 → bare `bu` stems per _ipc.py:43); `BH_TMP_DIR="$BH_HOME/tmp"`. BU_NAME gate: case pattern `""|*[!A-Za-z0-9_-]*` ⇒ stderr `invalid BU_NAME: $NAME`, exit 2, BEFORE any dir is created.

### Decisive source
```bash
DEV_ID="$(printf '%s' "$ROOT" | cksum | awk '{print $1}')"
NAME="${BU_NAME:-default}"
case "$NAME" in
  ""|*[!A-Za-z0-9_-]*) echo "invalid BU_NAME: $NAME" >&2; exit 2 ;;
esac
export BH_HOME="${BH_HOME:-$ROOT/.browser-harness-dev}"
if [ -z "${BH_RUNTIME_DIR:-}" ]; then
  export BH_RUNTIME_DIR="/tmp/bh-dev-$DEV_ID/runtime"
  export BH_RUNTIME_DIR_SHARED="${BH_RUNTIME_DIR_SHARED:-1}"
fi
```

**Flow:** resolve ROOT from BASH_SOURCE (symlink-proof `cd+pwd` physical path) → derive DEV_ID → validate BU_NAME (fail fast, nothing created) → export missing env with operator-override preserved (`${VAR:-default}` never clobbers) → pick first available interpreter and `exec` (shell is replaced, no wrapper process lingers).
**Invariant:** every export is conditional (`:-`), so an operator's explicit BH_* layout wins over dev defaults; DEV_ID is computed from the RESOLVED path so two clones of the same repo get different /tmp namespaces while re-clones at the same path reuse them; the SHARED=1 pairing matters because _ipc.py only emits bare `bu` stems when the caller-supplied runtime dir is per-instance — the launcher deliberately opts INTO shared-stem mode since its dir already carries the DEV_ID namespace; validation runs BEFORE side effects because the same name becomes socket/pid/log filename fragments downstream (_check would raise later inside Python, after dirs exist).
**Probe:** From repo root: `grep -n 'A-Za-z0-9_-' browser-harness` → exactly 1 hit at :9 (case gate); `grep -c 'invalid BU_NAME' browser-harness` → 1; `grep -n 'venv/bin/python\|uv --directory\|PYTHONPATH=' browser-harness` → :25/:26/:30/:33 ladder; live value check `printf '%s' "$(readlink -f .)" | cksum | awk '{print $1}'` yields the DEV_ID baked into `/tmp/bh-dev-<id>/runtime`. No unit test covers the bash script — coverage caveat (deterministic shell anchors).
**Anchored at the repo root** (the launcher lives at the checkout top, next to pyproject.toml).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "runtime stem shared tmp dir", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt path-cksum dev namespacing + validate-before-side-effect + override-preserving exports for any tool that spawns per-checkout daemons. Adapt env-var names. Omit the uv tier if your environments are always venv-managed.
