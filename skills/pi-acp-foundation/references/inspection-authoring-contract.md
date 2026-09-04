<!-- capsule-v2 -->
# Inspection authoring contract — how do you let a repository contribute scripted lint rules to a host IDE inspection pass?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** An adapter runs repo-owned inspection scripts after every turn (owned by repo-kts-inspection-extension.md). What does the REPO-SIDE authoring contract owe the script author — so a broken script degrades to a diagnostic instead of failing the turn, and the rules stay maintainable?

## One localInspection per script, WARNING level, per-file scope, degraded-not-fail
**Path/Symbol:** `inspections/README.md` (whole, 1628B) — gate linkage :5-16, authoring rules :18-23, testing recipe :25-28. `inspections/no-any.inspection.kts` (whole, 924B) — the shipped exemplar: declared-`any` finder with an `as any` cast exemption.
**Signature:** one `localInspection { psiFile, inspection -> ... }` lambda per script; findings registered via `inspection.registerProblem(element, "message")`; the inspection registered at `HighlightDisplayLevel.WARNING` inside an `InspectionKts(id = ..., localTool = ..., name = ..., htmlDescription = ..., level = ...)`.
**Data Shape:** a script is a Kotlin KTS file under `inspections/` ending `.inspection.kts` (discovery contract owned by repo-kts-inspection-extension.md: name-sorted, ≤8 scripts, ≤64KB each). The gate folds findings into the regular IDE inspection report (`.pi/work/ide-inspections/<sessionId>/<ts>.json`) and counts them in the `IDE inspection:` chat summary; a script that fails to compile surfaces as a diagnostic in the report and the summary gains a `custom inspections degraded` note — the turn NEVER fails. The whole gate is disabled by `PI_ACP_ENFORCE_IDE_INSPECT=0`.

### Decisive source
```kotlin
// no-any.inspection.kts — flags DECLARED 'any' but exempts 'as any' casts on untyped
// external data, per the repo's AGENTS.md policy. The exemption is a parents() scan.
val declaredAnyInspection = localInspection { psiFile, inspection ->
    psiFile.descendants()
        .filter { it.text == "any" && it.javaClass.simpleName != "LeafPsiElement" }
        .filter { node ->
            node.parents(withSelf = false).none { p -> p.javaClass.simpleName == "TypeScriptAsExpressionImpl" }
        }
        .forEach { inspection.registerProblem(it, "Avoid declaring 'any' — use an explicit type or unknown") }
}
```

**Flow:** author writes one script = one `localInspection` (per-file rules only: `localInspection` sees one file per run; project-wide rules need `globalInspection` + a full Qodana analysis, explicitly out of scope for the gate) → the post-turn gate discovers and runs it per changed file within the global call budget → findings merge into the report; compile failures degrade to a diagnostic + `custom inspections degraded` summary note. The `InspectionKts` `id` is referenced from `qodana.yaml` when the scripts are later run by Qodana in CI (linkage documented in the README; qodana.yaml itself currently carries no inspection includes — see qodana-license-constrained-linter.md). Testing recipe: use the IDE tools `ide_idea_run_inspection_kts` (returns `compilationSuccess`, `inspectionResultMessage`, `foundProblems`), `ide_idea_generate_inspection_kts_examples`, and `ide_idea_generate_inspection_kts_api`.
**Invariant:** a broken script can never fail the turn — degradation is the contract, enforced adapter-side (worst-status-wins per script, owned by repo-kts-inspection-extension.md) and documented repo-side. Rules stay per-file and WARNING-level so the gate stays advisory.
**Probe:** no direct unit test pins the KTS scripts themselves (recorded caveat); the adapter-side budget/retry/degradation behavior is pinned by `test/unit/ide-inspection.test.ts` (executed green at the pin), and the end-to-end proof is `scripts/smoke-ide-inspect.mjs` asserting `kts[0].status==='ok'` in the persisted report.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "localInspection registerProblem InspectionKts inspection script authoring", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the authoring contract shape: one rule per script, per-file scope only, advisory (WARNING) severity, findings registered through the host's problem API, and the degraded-not-fail guarantee documented where authors will read it. Adapt the script language and the IDE tool names to your host's scripted-inspection surface. Omit the Qodana id linkage unless your CI runs the same scripts. Adapter-side machinery is owned by repo-kts-inspection-extension.md + post-turn-inspection-gate.md; this capsule owns the repo-side contract and the shipped exemplar. No direct test for the scripts themselves at this pin.
