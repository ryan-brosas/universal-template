<!-- capsule-v2 -->
# Usage idioms — are null, collections, and async handled idiomatically?

**Source:** Effective Dart — Usage. **Question:** Does code use modern Dart features concisely and safely?

## Null and collections seam
**Path/Symbol:** Dart application logic using null safety and collections.
**Signature:** no explicit null init; collection literals; interpolation.
**Data Shape:** `isEmpty` checks; tear-offs.

### Decisive pattern
```dart
String greet(String name) => 'Hello, $name';

bool hasPending(List<Job> jobs) => jobs.isNotEmpty;

final ids = users.map(User.id).toList();

void onTap() => handleTap;
```

**Flow:** omit `= null` on nullable locals → use `?.` / promotion / null-check patterns → prefer `'$x'` interpolation → collection literals `[...]`/`{...}` → `.isEmpty`/`.isNotEmpty` not `.length` → tear-off instead of `(x) => fn(x)` when equivalent → relative imports within package.
**Invariant:** `if (list.length == 0)`, explicit `= null`, or importing another package's `src/` fails review.
**Probe:** analyzer lints (`prefer_is_empty`, `avoid_init_to_null`); import path review.

## Async and errors seam
```dart
Future<User> loadUser(String id) async {
  try {
    return await _client.fetchUser(id);
  } on HttpException catch (e) {
    logger.warning('fetch failed: $e');
    rethrow;
  }
}
```

**Flow:** prefer `async`/`await` over raw `.then` chains → don't mark `async` without await → `on SpecificException catch` not bare catch → `rethrow` to propagate → throw `Error` subtypes only for programmer bugs → don't catch `Error`.
**Invariant:** empty `catch (e) {}`, bare `catch` without rethrow/logging, or catching `Error` fails review.
**Probe:** `dart analyze`; tests for error paths.

## Verdict
null-safe idioms, collection literals, async/await, typed catches. Learning note: `dart-style-learning-note.md`.
