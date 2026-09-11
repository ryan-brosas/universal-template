<!-- capsule-v2 -->
# FUS collector registration — statistics.applicationUsagesCollector / projectUsagesCollector / gotItTooltipAllowlist

**Source:** JetBrains IDE installed builds `PyCharm PY-262.9437.214` / `WebStorm WS-262.9437.145` / `Rider RD-262.8665.400`; Codebase Memory `jetbrains-pycharm`. **Question:** How does feature-usage telemetry register collectors, and why is the allowlist EP the load-bearing half for a privacy-respecting port?

## Collector + allowlist pair
**Path/Symbol:** `intellij.platform.ide.impl.jar:META-INF/PlatformExtensionPoints.xml` — `<extensionPoint name="statistics.applicationUsagesCollector" beanClass="com.intellij.internal.statistic.service.fus.collectors.UsageCollectorBean" dynamic="true"/>`, `<extensionPoint name="statistics.projectUsagesCollector" beanClass="...UsageCollectorBean" dynamic="true"/>`, `<extensionPoint name="statistics.gotItTooltipAllowlist" beanClass="com.intellij.internal.statistic.collectors.fus.ui.GotItTooltipAllowlistEP" dynamic="true"/>`.
**Signature:** `<statistics.applicationUsagesCollector implementation="<UsageCollector FQN>"/>` | `<statistics.projectUsagesCollector implementation="<UsageCollector FQN>"/>` | `<statistics.gotItTooltipAllowlist prefix="<tooltip-show-id-prefix>"/>`.
**Data Shape:** collectors are IDE-global vs per-project metric bundles; the allowlist EP carries a plain STRING PREFIX (no class) — each row whitelists one "Got It" tooltip id family for metrics reporting.

### Decisive source
```xml
<!-- py census: applicationUsagesCollector x85, projectUsagesCollector x56, allowlist x12 (occurrence-exact) -->
<statistics.projectUsagesCollector implementation="com.intellij.xdebugger.impl.breakpoints.BreakpointsStatisticsCollector"/>
<!-- intellij.platform.debugger.impl.jar:...content.xml -->
<statistics.gotItTooltipAllowlist prefix="extract.method.gotit.navigate"/>
<statistics.gotItTooltipAllowlist prefix="extract.method.signature.change"/>
<statistics.gotItTooltipAllowlist prefix="changes.view.toolwindow"/>
```

**Flow:** runtime enumerates declared collectors → metrics service validates every reported event/group against DECLARED ids and prefixes → undeclared = dropped at validation, not at collection.
**Invariant:** telemetry ids are deny-by-default: a collector or tooltip id absent from these rows never reaches reports. Wrong port: shipping collector classes without their manifest rows (metrics silently empty), or copying prefixes without renaming your own tooltip ids (you report ANOTHER product's events).
**Probe:** from install root: `for j in lib/*.jar; do unzip -p "$j" '*.xml' 2>/dev/null | grep -o '<statistics\.applicationUsagesCollector\b' | wc -l; done | awk '{s+=$1} END{print s}'` → 85 (py); `<statistics\.projectUsagesCollector\b` → 56; `<statistics\.gotItTooltipAllowlist\b` → 12.

## Get live surrounding code
**Retrieve:** manifest-only plane — no BM25 symbol surface. Deterministic primitive:
```bash
for j in lib/*.jar; do unzip -p "$j" '*.xml' 2>/dev/null | grep -H --label="$j" 'BreakpointsStatisticsCollector'; done | head -2
```
→ debugger jar AND pro jar both carry the row at pin PY-262.9437.214.

## Verdict
Adopt declare-to-whitelist telemetry with prefix-scoped UI-event families; adapt group-id scheme; omit IntelliJ's FUS upload pipeline. Boundary: fus-telemetry-metadata-plane owns dictionaries/usage-priors; this capsule owns COLLECTOR + ALLOWLIST REGISTRATION.
