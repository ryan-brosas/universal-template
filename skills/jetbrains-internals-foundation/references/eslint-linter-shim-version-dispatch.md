<!-- capsule-v2 -->
# ESLint linter shim dispatch — how does one linter service absorb eslint v8-vs-legacy API divergence AND eslint-config-standard v17?

**Source:** JetBrains IDE installed build `WebStorm 262.9437.145`; Codebase Memory `jetbrains-webstorm`. **Question:** above.

## Major-prefix factory + typed request vocabulary mirroring the JVM enum
**Path/Symbol:** `plugins/javascript-eslint/languageService/eslint/bin/eslint-plugin-provider.js`:`ESLintPluginFactory.create` (:7-26); protocol vocabulary `eslint-api.js` (:4-23).
**Signature:** `factory.create(state) -> { languagePlugin }` with `state = { linterPackageVersion: string, standardPackagePath?: string }`.
**Data Shape:** request commands `GetErrors` | `FixErrors`; responses carry `request_seq`+`command`; file classes enum `FileKind = { ts:"ts", html:"html", vue:"vue", jsAndOther:"js_and_other" }` — values mirror `com.intellij.lang.javascript.linter.eslint.EslintUtil.FileKind` (cross-language contract stated in source comment).

### Decisive source
\`\`\`js
create(state) {
  if (state.standardPackagePath != null) {
    var dotIndex = state.linterPackageVersion.indexOf(".");
    var majorVersion = dotIndex > 0 ? state.linterPackageVersion.substring(0, dotIndex) : "";
    if (+majorVersion >= 17) {                       // eslint-config-standard v17 needs its own shim
      var Standard17Plugin = require('./standard17-plugin').Standard17Plugin;
      return { languagePlugin: new Standard17Plugin(state) };
    }
  } else {
    … if (+majorVersion >= 8) { return { languagePlugin: new ESLint8Plugin(state) }; }
  }
  var ESLintPlugin = require('./eslint-plugin').ESLintPlugin;   // pre-8 legacy fallback
  return { languagePlugin: new ESLintPlugin(state) };
}
\`\`\`

**Flow:** JVM detects the user's eslint (+ optional standard) install and sends versions → factory parses MAJOR as substring-before-first-dot coerced with unary `+` → standard-present && major≥17 ⇒ Standard17Plugin; else major≥8 ⇒ ESLint8Plugin; else legacy ESLintPlugin → chosen plugin adapts config loading/fix application to that API generation over the shared GetErrors/FixErrors vocabulary.
**Invariant:** (1) dispatch keys off MAJOR ONLY with a deliberate non-semver parse — no dependency, tolerant of weird version strings (`dotIndex > 0` guards empty/odd forms, falls back to legacy); (2) the standard-vs-eslint branch has PRECEDENCE over the version branch; (3) the wire vocabulary and FileKind VALUES are a fixed cross-process contract with the JVM side — rename neither unilaterally.
**Probe:** `node --check` on eslint-plugin-provider.js and eslint-api.js → OK (executed). Coverage: both no_recorded_issue. Live Retrieve pinned below; interior of the three plugin shims is next-pass scope.

## Get live surrounding code
**Retrieve:**
\`\`\`ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-webstorm", query: "ESLintPluginFactory", limit: 5 });
// hit: …javascript-eslint.languageService.eslint.bin.eslint-plugin-provider.ESLintPluginFactory @ eslint-plugin-provider.js:5-6
\`\`\`

## Verdict
Adopt the dispatcher shape (major-prefix parse, precedence-ordered special cases, legacy fallback) for ANY service embedding a fast-moving third-party linter across API generations. Adapt the threshold set (8/17 here) to your supported range. Omit the IntelliJ FileKind mirror only if your host has no cross-language enum — otherwise keep value-level parity and say so in a source comment like this one does.
