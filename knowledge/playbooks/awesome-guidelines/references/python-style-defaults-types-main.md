<!-- capsule-v2 -->
# Defaults, types, and main — are footguns and entrypoints handled?

**Source:** Google pyguide §2.12, §3.17, §3.19; PEP 8 default-arg spacing. **Question:** Are mutable defaults absent, public APIs typed, and scripts import-safe?

## Mutable defaults seam
```python
def append_item(item, bucket=None):
    if bucket is None:
        bucket = []
    bucket.append(item)
    return bucket
```

**Flow:** use `None` sentinel for mutable/object defaults → assign inside function → immutable defaults (`()`, `0`, `""`) OK.
**Invariant:** default arg expressions run **once** at def time — lists/dicts/time/flags must not be defaults.
**Probe:** ruff B006 / flake8 B008 clean; grep `def .+=\[\]` and `def .+=\{\}` empty.

## Types & main seam
```python
def fetch_user(user_id: int) -> User | None:
    ...

def main() -> None:
    ...

if __name__ == "__main__":
    main()
```

**Flow:** annotate public function params/returns → skip redundant `self`/`__init__` return → put script logic in `main()` → guard execution.
**Invariant:** importing a module must not run network/cli side effects — top level is definitions and constants only.
**Probe:** `mypy`/`pyright` on public package surface; import module in test without mocking argv/network.

## Verdict
Adopt None-sentinel mutable defaults, typed public APIs, `main` guard. Learning note: `python-style-learning-note.md`.
