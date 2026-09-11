<!-- capsule-v2 -->
# Documentation — are public APIs documented with /// comments?

**Source:** Effective Dart — Documentation. **Question:** Can consumers understand API from doc comments alone?

## Doc comment seam
**Path/Symbol:** public classes, members, library entrypoints.
**Signature:** `///` documentation; one-sentence summary first.
**Data Shape:** prose for params/returns; `[Type]` references.

### Decisive pattern
```dart
/// Loads the user with the given [id].
///
/// Returns `null` if no user exists.
Future<User?> loadUser(String id) async {
  ...
}

/// Whether the connection is currently active.
bool get isConnected => _connected;
```

**Flow:** `///` on public types/members → first sentence standalone summary → boolean properties start with "Whether" → side-effect methods third-person verb → value-returning methods noun phrase → use `[identifier]` links → doc comment before metadata annotations → don't document both getter and setter.
**Invariant:** exported API without summary doc, block `/** */` for member docs, or HTML-heavy docs fail review.
**Probe:** `dart doc` build; public API doc coverage check in review.

## Comment quality seam
**Flow:** comments as sentences → prefer brevity → avoid redundant restatement of identifier → code samples in fenced blocks with backticks.
**Invariant:** commented-out code left in place of deletion fails review (use VCS).
**Probe:** review for stale block comments; doc generation warnings.

## Verdict
/// summaries, Whether for booleans, linked references, dart doc clean. Learning note: `dart-style-learning-note.md`.
