# Ecosystem setup patterns

Concise starting shapes only. **The project's own scripts, version files, and lockfiles always win over these recipes** — inspect first (`SKILL.md` step 1); if the project declares `npm run verify`, CI runs that. Action refs are placeholders (`<...>`): resolve the current trusted release and pin the full SHA at authoring time (see `security.md`); Dependabot keeps them current.

## Node / TypeScript

- Detect: `package.json`, lockfile flavor (`package-lock.json` / `pnpm-lock.yaml` / `yarn.lock` / `bun.lock`), `packageManager:` field, workspaces (`workspaces`, `pnpm-workspace.yaml`), `turbo.json`/`nx.json`.
- Setup: official Node setup action with its built-in package-manager cache; enable corepack or the package-manager action when the lockfile demands a specific manager.
- Install: deterministic mode matching the manager (`npm ci`, frozen-lockfile variants). Never mutate the lockfile in CI.
- Run: the project's own scripts (`lint`, `typecheck`, `test`, `build`). Cache: package-manager store via setup cache; build outputs only when reused between jobs.
- Version source: `engines`/`packageManager`/`.nvmrc`/`.tool-versions` — reproduce what the project supports, not "latest".

## Python

- Detect: `pyproject.toml` (project/uv/poetry/hatch), `requirements*.txt`, `uv.lock`/`poetry.lock`, `tox.ini`/`noxfile.py`, version pins (`.python-version`, mise).
- Setup: official Python setup action with pip cache, or uv (fast, lockfile-aware) when the project uses it.
- Install: locked/sync mode (`uv sync --frozen`, `poetry install --sync`, `pip install -c constraints.txt`).
- Run: project scripts or task runner (`pytest`, `ruff`, `mypy` as the project wires them — e.g. via `tox`/`nox`/`make`).
- Matrix only when multiple supported Python versions are real (library) — single pinned version for an app.

## Rust

- Detect: `Cargo.toml`, workspace members, `rust-toolchain.toml`, `Cargo.lock` (committed for binaries, often not for libraries).
- Setup: Rust toolchain action pinned to the project's toolchain file; cache the cargo registry/git/target dirs keyed on `Cargo.lock` + `Cargo.toml` (or a maintained Rust cache action — pinned and reviewed).
- Run: `cargo fmt --check` / `clippy -- -D warnings` / `test` / `build --release` as the project defines; `cargo deny`/`audit` where the project uses them.
- Release binaries → build per supported triple in a matrix ONLY for platforms the release actually targets (`release-deploy.md`); consider artifact attestations for published binaries.

## Go

- Detect: `go.mod`/`go.sum`, `go.work` (multi-module), Makefile targets.
- Setup: official Go setup action with module cache; `go vet`/`golangci-lint`/`go test ./...` as the project wires them.
- Determinism: modules are lockfile-managed by `go.sum`; read-only cache keyed on `go.sum`.

## JVM (Maven/Gradle)

- Detect: `pom.xml` / `build.gradle(.kts)` + wrapper (`gradlew` must be committed; verify wrapper checksums where the project does), `.java-version`/mise.
- Setup: Java setup action with its built-in dependency cache keyed on the lockfile/wrapper; run `./gradlew check` / `mvn verify` — always through the wrapper, never a globally installed Gradle.
- Test reports: publish only on failure when they speed diagnosis.

## Elixir

- Detect: `mix.exs`, `mix.lock`, `.tool-versions`/mise (OTP + Elixir are paired — derive both from the project's versions), umbrella apps (`apps/`).
- Setup: official Elixir setup action (or BEAM-specific) respecting the OTP/Elixir pair; cache `deps/` keyed on `mix.lock` and `_build` keyed on lockfile + OTP/Elixir versions (mix currently lacks setup-action built-in caching — hand-roll only if it pays).
- Run: `mix format --check-formatted`, `mix compile --warnings-as-errors` (when the project treats warnings as errors), `mix test`.
- Services (Postgres for Ecto): service containers with health checks, `MIX_ENV=test`.
- Do not add a Node/frontend job merely because an `assets/` folder exists — check whether the project actually builds one.

## Containers

- Detect: `Dockerfile`(s), compose files, buildx needs.
- PR CI: build (and test) the image; never expose registry credentials to PR jobs.
- Publishing: trusted events only; multi-platform builds only for platforms actually shipped; consider attestations for published images.

## Cross-cutting

- Use the version source the project declares (`.tool-versions`, `mise.toml`, `.python-version`, `engines`, toolchain files) — CI must reproduce supported environments, not whichever is newest.
- Prefer project scripts (`make ci`, `just verify`, task runners) as the single job step; CI invokes, does not restate.
- Test-report annotations/artifacts only when they materially speed diagnosis (`patterns.md`).
