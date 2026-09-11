<!-- capsule-v2 -->
# Startup activity ladder — postStartupActivity vs backgroundPostStartupActivity vs applicationActivity vs vcsStartupActivity

**Source:** JetBrains IDE installed builds `PyCharm PY-262.9437.214` / `WebStorm WS-262.9437.145` / `Rider RD-262.8665.400`; Codebase Memory `jetbrains-pycharm`. **Question:** Which of the four startup hooks runs when, on which thread/scope, and what breaks if a porter hangs heavy work on the wrong rung?

## The four rungs
**Path/Symbol:** `intellij.platform.core.jar:META-INF/Core.xml` — `<extensionPoint name="postStartupActivity" interface="com.intellij.openapi.startup.ProjectActivity" dynamic="true"/>` and `<extensionPoint name="backgroundPostStartupActivity" interface="com.intellij.openapi.startup.ProjectActivity" dynamic="true"/>` (SAME interface, different scheduling); `intellij.platform.usageView.jar:META-INF/IdeCore.xml` — `<extensionPoint name="applicationActivity" interface="com.intellij.ide.ApplicationActivity" dynamic="false"/>`; `intellij.platform.vcs.impl.jar:META-INF/VcsExtensionPoints.xml` — `<extensionPoint name="vcsStartupActivity" interface="com.intellij.openapi.vcs.impl.VcsStartupActivity" dynamic="false"/>`.
**Signature:** `<postStartupActivity implementation="<ProjectActivity FQN>" [order]/>` | `<backgroundPostStartupActivity implementation="<ProjectActivity FQN>" [id] [os] [order]/>` | `<applicationActivity implementation="<ApplicationActivity FQN>"/>` | `<vcsStartupActivity implementation="<VcsStartupActivity FQN>"/>`.
**Data Shape:** project-scope suspend-coroutine activities (the two ProjectActivity EPs) vs application-scope boot finisher (`applicationActivity`) vs VCS-subsystem hook; only the two Core.xml EPs are `dynamic="true"` — the other two require restart to re-read.

### Decisive source
```xml
<!-- backgroundPostStartupActivity usage: intellij.platform.backend.workspace.impl.jar:...xml:23 -->
<backgroundPostStartupActivity implementation="com.intellij.platform.backend.workspace.impl.DelayedProjectSynchronizer"/>
<!-- applicationActivity usage: intellij.platform.builtInServer.impl.jar:...xml:53 -->
<applicationActivity implementation="org.jetbrains.ide.BuiltInServerManagerLauncher"/>
<!-- vcsStartupActivity usage: intellij.platform.vcs.dvcs.impl.jar:...xml:117 -->
<vcsStartupActivity implementation="com.intellij.dvcs.repo.VcsRepositoryManager$MyStartupActivity"/>
```

**Flow:** smart-mode entry → foreground `postStartupActivity` coroutines run to completion while the project load is still "in progress" → `backgroundPostStartupActivity` items are deferred off the critical path (name says when they run: after startup, in background) → `applicationActivity` fires once per APPLICATION boot (BuiltInServerManager starts the IDE's HTTP port here) → `vcsStartupActivity` activates VCS-specific bookkeeping.
**Invariant:** anything that must delay "project ready" belongs on `postStartupActivity`; anything that would slow first paint belongs on the background rung. Wrong port: registering a network-syncing initializer as foreground `postStartupActivity` (startup stalls), or expecting `applicationActivity`/`vcsStartupActivity` changes to hot-reload (both are `dynamic="false"`).
**Probe:** from install root: `unzip -p lib/intellij.platform.core.jar META-INF/Core.xml | grep -c 'name="postStartupActivity"'` → 1; `| grep -c 'name="backgroundPostStartupActivity"'` → 1. Occurrence census (py): `for j in lib/*.jar; do unzip -p "$j" '*.xml' 2>/dev/null | grep -o '<postStartupActivity ' | wc -l; done | awk '{s+=$1} END{print s}'` → 114; same with `<backgroundPostStartupActivity ` → 65.

## Get live surrounding code
**Retrieve:** manifest-only plane — no BM25 symbol surface for these EP tokens. Deterministic primitive:
```bash
for j in lib/*.jar; do unzip -p "$j" '*.xml' 2>/dev/null | grep '<applicationActivity '; done | head -3
```
→ BuiltInServerManagerLauncher + ToolboxRestLauncher among py's 41 at pin.

## Verdict
Adopt the two-rung project-lifecycle split (foreground vs deferred) plus app-level and subsystem-specific ladders as separate EPs; adapt names; omit coroutine/`ProjectActivity` Kotlin machinery beyond the contract. Coverage caveat: counts top-level-lib only; minified single-line XMLs REQUIRE occurrence counting (`grep -o | wc -l`), line-based `grep -c` undercounts. Boundary: dumb-aware indexing interplay lives in platform docs, not this capsule.
