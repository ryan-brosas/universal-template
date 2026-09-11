<!-- capsule-v2 -->
# rust-dead-plane-map — which source files LOOK like the product but are NOT compiled?

**Source:** meetily (MIT) `main@0281737d`; Codebase Memory `ext-meetily`. **Question:** Before porting any meetily Rust module, how do I tell live code from abandoned planes that still sit in the tree (and even in the graph)?

## lib.rs module list is the liveness oracle
**Path/Symbol:** `frontend/src-tauri/src/lib.rs:38-56` (the complete `pub mod` list); orphans: `src/audio_v2/*` (8 files), `src/audio/stt.rs`, `src/audio/core-old.rs`, `src/lib_old_complex.rs` (2437L), `src/audio/recording_commands.rs.backup`, `src/audio/recording_saver_old.rs`.
**Signature:** n/a — structural fact.
**Data Shape:** LIVE modules declared in lib.rs: analytics, api, audio, config, console_utils, database, notifications, ollama, onboarding, openai, anthropic, groq, openrouter, parakeet_engine, state, summary, tray, utils, whisper_engine. NOT declared anywhere: the entire `audio_v2` plane (ModernRecorder/ModernAudioStream/AudioMixer/normalizer/resampler/sync — its own files import a nonexistent `crate::audio::core` and would not compile), `audio/stt.rs` (imports `screenpipe_core`, `crate::pyannote`, `crate::deepgram` — none exist), both `*_old*` files.

### Decisive source
```bash
grep -rEn '^\s*(pub )?mod (stt|core-old|core)\b' --include='*.rs' src/   # → 0 hits
grep -rn 'audio_v2' --include='*.rs' src/ | grep -v '^src/audio_v2/'      # → 0 hits
```

**Flow:** cargo only compiles what the module tree reaches; these files are invisible to the compiler yet VISIBLE to grep, the codebase-memory graph (`ext-meetily.frontend.src-tauri.src.audio.stt.*` nodes exist!), and naive "read the repo" passes.
**Invariant:** Any capsule citing `stt.rs cleanup_overlap`/`longest_common_word_substring` or any `audio_v2/*` type describes UNMAINTAINED CODE — behavior may drift from the real pipeline without ever breaking a build. The live transcription path is `whisper_engine/whisper_engine.rs` + `parakeet_engine/` instead.
**Probe:** battery T40 = external `audio_v2` references == 0; T41 == 0 mod declarations for stt/core-old/core (negative probes pinned as BY-CONSTRUCTION zeros).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meetily", query: "TranscriptionResult cleanup_overlap", limit: 5, fields: ["signature", "name", "file"] });
// returns hits — but cross-check the file against lib.rs's pub mod list BEFORE trusting it
```

## Verdict
Adopt the check-the-mod-tree-first discipline for ANY Tauri/Rust repo; omit every orphaned plane from porting; treat graph hits inside dead files as historical metadata. Pinned via deterministic battery at pin.
