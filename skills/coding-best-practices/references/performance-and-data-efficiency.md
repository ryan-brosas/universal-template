# Performance and data efficiency

## Profile before optimizing

- Measure with a profiler or timed benchmark on representative data — do not vectorize or cache by instinct.
- Record baseline numbers in the PR or commit message when the change is performance-motivated.

## Data-oriented shortcuts (when measured)

- **Vectorize** hot loops (NumPy/Pandas/polars/SQL) instead of Python `for` over millions of rows.
- **Chunk** streams that do not fit memory; bound batch sizes.
- **Compress** serialized payloads when I/O dominates — verify decompress cost.
- **Parallelize** only when work is CPU-bound and overhead is justified; watch contention and GIL limits.

## Readability tradeoff

- A clear loop beats opaque micro-optimization unless profiling proved the hot path — document the proof in a comment linking to benchmark or issue.

## Do not optimize speculatively

- Aligns with YAGNI and `steer-outcomes-not-behavior`: ship correct first, optimize when gates or profiles demand it.

## Mechanical gates

- Benchmark tests in CI only when stable (no flaky timing assertions on shared runners).
- Regression tests for **correctness** always; performance tests optional and environment-pinned.

## Leaf skills

- Stack-specific: relevant `*-foundation` leaves (e.g. DuckDB, data pipelines)
- Review scope creep from "optimization" PRs: `code-review-and-quality`
