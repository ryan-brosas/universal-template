<!-- capsule-v2 -->
# Fail-safe request-log SPI — how do you add optional per-request NDJSON logging at dozens of provider call sites so that the ABSENCE of a logger can never fail inference?

**Source:** goose Apache-2.0 `main@2eb3ab1001dedb5ab09a6ed60158adfc248bac56`; Codebase Memory `goose`. **Question:** how do you structure a process-global request logger whose installation is one-shot, whose absence is a silent no-op at every call site, and whose per-request handles stay total?

## One-shot global logger + total Option-handle extension
**Path/Symbol:** `crates/goose-provider-types/src/request_log.rs` — `static LOGGER: OnceLock<Arc<dyn RequestLogger>>` (14), `install_logger` (27–29), `RequestLogger` trait (31–33), `RequestLogHandle` trait (35–37), `start_log` (66–88), `impl LoggerHandleExt for Option<Box<dyn RequestLogHandle>>` (99–134).
**Signature:** `fn install_logger<R: RequestLogger + 'static>(r: R) -> Result<(), LoggerAlreadyInstalled>`; `fn start_log<M: Serialize, P: Serialize>(model_config: M, payload: P) -> Result<Option<Box<dyn RequestLogHandle>>, LogError>`; `trait LoggerHandleExt { fn write<Payload: Serialize>(&mut self, data: &Payload, usage: Option<&Usage>) -> Result<(), LogError>; fn error<E: Display>(&mut self, error: E) -> Result<(), LogError>; }`.
**Data Shape:** opening NDJSON line `{"model_config":…,"input":…}`; continuation lines `{"data":…,"usage":…}` or `{"error":"…"}`. Handles are single-request, boxed, `Send`.

### Decisive source
```rust
// request_log.rs — absence of a logger is SUCCESS with no handle, and every
// operation on Option<Box<dyn RequestLogHandle>> treats None as Ok(())
// (logging can never fail inference):
let logger = if let Some(logger) = LOGGER.get() { logger } else { return Ok(None); };
let mut handle = logger.start()?;
let payload = json!({ "model_config": model_config, "input": payload });
handle.write(serialize(&payload)?.as_str())?;
Ok(Some(handle))
```

**Flow:** startup installs ONE process-global impl — goose's `providers/utils.rs:init_goose_request_log` wraps `static INIT_LOGGER: OnceLock<Result<()>>` + `get_or_init`, so even an INSTALL FAILURE is memoized and never retried per request; the SDK path installs its own adapter at `goose-sdk/src/bindings.rs:174` → each provider call site runs `let mut log = start_log(model_config, &payload)?;` writing the opening line → response/stream paths emit `write(&data, usage)` / `error(e)` continuation lines (retrying providers simply call `start_log` again, cf. openrouter.rs:571→579) → the CLI `FileLogHandle` Drop-finishes its temp `llm_request.{uuid}.jsonl` into a rename ladder keeping the newest `LOGS_TO_KEEP=10` files (rotation skipped while thread is panicking).
**Invariant:** uninstalled logger ⇒ `start_log → Ok(None)` and every handle op ⇒ `Ok(())` — totality holds at ALL call sites (~25 provider files); installation is one-shot (`LoggerAlreadyInstalled`) and its outcome memoized; serialization failures become `LogError` only once a logger actually exists.
**Probe:** honest caveat — `request_log.rs` carries NO `#[cfg(test)]` unit test. Pinned instead by: (a) call-site totality survey — `start_log(` appears in 25+ provider files, every site binding the `Option` handle (goose-providers/src/{anthropic.rs:184, openai.rs:304+798, google.rs:193, ollama.rs:423, snowflake.rs:334, databricks*.rs}; goose/src/providers/{bedrock.rs:672+924+969, githubcopilot.rs:460+508+540, codex.rs:731, …}); (b) the module compile-runs green inside the observed `cargo test -p goose-provider-types --lib cache` subset (19 passed / 0 failed this pass; full-lib 551-passed GREEN recorded in pass-2 evidence); (c) consumer backend read directly (utils.rs 104–187 rotation ladder + panic guard).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "goose", query: "RequestLogger install_logger start_log LoggerHandleExt RequestLogHandle", limit: 12 });
// located: request_log.rs:install_logger 27-29, start_log 66-88, RequestLogHandle 35-37, LoggerHandleExt.write/error 91-96;
// consumers: goose-sdk bindings.rs RequestLogger interface 134-137, goose-local-inference lib.rs:720
```

## Verdict
Adopt the `OnceLock` one-shot SPI, the `Option`-handle extension trait making absence a no-op, the memoized-install pattern (cache the `Result` too), and the three NDJSON line shapes. Adapt backends freely — goose rotates on-disk JSONL files, the SDK forwards over bindings. Omit the CLI retention policy (keep-newest-10) if your host has its own. Coverage caveat: this module has no direct unit tests anywhere in the repo; the grep survey plus compile-green runs are the probe evidence, stated as such.
