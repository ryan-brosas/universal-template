# Ship Bend rules without shipping the compiler

Use when Bend rules work through a development loader but the same host helpers
must ship to a browser or precompiled executable. The useful distinction is
**compiler availability at build time versus rule availability at runtime**.
A loader-backed unit test proves neither bundling nor deployment independence.

This path assumes the pinned compiler can emit JS for the required module graph.
It does not replace a native-backend probe, or require removing a runtime compiler
from an application whose product is compiling user-supplied programs.

## Sequence

1. **Trace the actual consumer first.** Follow a public host helper through its
   imports to Bend. Identify browser, source-run and executable entry points.
   If a host loader pulls filesystem, process or compiler dependencies into that
   graph, moving the rule call alone cannot make it browser-safe. Use the pinned
   compiler's source/guide to locate its JS-emission boundary; do not copy a
   compiler API from another revision.
2. **Make deployment the regression.** Bundle a small entry that imports the
   real host helper, not a second implementation or direct Bend-only demo. Call
   representative rules and assert observable results. Run the emitted JS in a
   fresh context with only the globals it legitimately needs; for pure helpers,
   a bare VM with a captured console can exclude Bun, Node, filesystem and
   compiler access. Record any failure before replacing the integration.
3. **Move compilation outside the runtime graph.** Have a build plugin intercept
   static `.bend` imports, validate the project's compiler pin before importing
   the compiler, and return the pinned compiler's emitted JS to the bundler.
   Share the compiler guard with existing tooling. Register that plugin in each
   shipping build, not only the test runner. A generated-module build step is
   another option when the bundler lacks plugins; avoid a hand-maintained JS copy
   of the Bend rules.
4. **Keep the adapter lossless, not authoritative.** Share browser-safe value
   conversions between host consumers. Convert only the data the model needs;
   keep payloads or metadata it cannot represent host-owned. For ordering or
   selection, map results back to original objects with an identity scheme that
   cannot collapse valid rows; test duplicates when allowed. Apply only fields
   actually changed by Bend. Do not retain a parallel TS rule implementation as
   a fallback.
5. **Scope development activation.** Prefer explicit preload flags on commands
   that import `.bend`; build scripts register the same plugin directly. A
   directory-wide preload also reaches unrelated Bun processes started there.
   Use it only when that scope is intentional and verified, not to repair one
   missing registration. Check argument parsing on the installed Bun version:
   `bun test --preload ./scripts/bend-preload.ts …` puts the flag after the test
   subcommand; file execution uses `bun --preload … entry.ts`. Exercise the
   package script too, since accidental script recursion can hide behind a
   working direct invocation.

## Evidence and limits

Inspect the bundle's source map or module graph: the intended Bend module should
be present and compiler/tooling modules absent. Pair that inspection with the
restricted-runtime behavior assertion; string absence alone proves little.
Then run relevant parity/conversion checks and the actual shipping build.
A browser-helper probe does not prove a native executable works independently;
probe that artifact separately if claimed.

Keep gate statuses and skip counts honest using
[false-green-gates](../../false-green-gates/README.md). A timed GUI run reaching
mount establishes startup, not clean termination or exercised interactions.
