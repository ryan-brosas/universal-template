<!-- capsule-v2 -->
**Source:** teable `record-history-cold.module.ts` @ pin `06a4461e`
**Question:** How do you stop auxiliary worker hosts from becoming competing queue consumers?
**Path/Symbol:** `RecordHistoryColdCoreModule` (services only), `RecordHistoryColdModule` (core + EventJobModule.registerQueue + Processor)
**Signature:** CoreModule provides/exports StorageService, ReadService, Flusher, Compactor with NO queue registration; only the outer module registers `RECORD_HISTORY_COLD_QUEUE` and the BullMQ processor.
**Decisive source:** :13-21 — "services only — no queue, no worker. EVERY importer except the app root belongs here: feature modules (record/table open-api), one-off tools (the EE CLI runner), and auxiliary worker entrypoints that compose feature modules. Importing the full module below instead silently turns the host process into a competing cold-queue consumer — on 2026-07-08 the BYODB migration worker picked up a flush that way while still running old code mid-rolling-deploy, and broke the catch-up chain."
**Flow/Invariant:** Two-tier DI: consumers needing the SERVICES import CoreModule; only the app root imports the full Module. The comment names the exact production incident class (auxiliary worker consuming jobs with stale code).
**Probe (direct test):** `grep -c 'EventJobModule' apps/nestjs-backend/src/features/record-history-cold/record-history-cold.module.ts` → `2` (import line + one registerQueue usage); `grep -c 'competing cold-queue consumer' ...` → `1`. Consumers verified: app.module, record/table open-api modules import the CORE module.
**Retrieve:** `echo '{"project":"teable","pattern":"RecordHistoryColdCoreModule","limit":5}' | codebase-memory-mcp cli search_code`
**Verdict:** adopt — core/services vs queue/worker module split generalizes to any BullMQ deployment.
