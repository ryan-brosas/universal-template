<!-- capsule-v2 -->
# Design and API — are types, classes, and names designed for maintainability?

**Source:** Effective Dart — Design. **Question:** Is the public surface intentional about extension, typing, and equality?

## Type annotation seam
**Path/Symbol:** public library API signatures and fields.
**Signature:** explicit return/parameter types on declarations; `final` where possible.
**Data Shape:** class modifiers control subclassing.

### Decisive pattern
```dart
final class UserService {
  UserService(this._client);

  final HttpClient _client;

  Future<User?> findByEmail(String email) {
    ...
  }
}

class Point {
  const Point(this.x, this.y);

  final int x;
  final int y;

  @override
  bool operator ==(Object other) =>
      other is Point && other.x == x && other.y == y;

  @override
  int get hashCode => Object.hash(x, y);
}
```

**Flow:** annotate public return types and parameters → annotate non-obvious top-level/field types → prefer `final` fields → use `final class` / modifiers to prevent unintended subclassing → const constructors when supported → override `hashCode` with `==` on value types → avoid custom equality on mutable classes.
**Invariant:** public method missing return type, mutable class with `==`, or `getFoo` naming for side-effect API fails review.
**Probe:** strict analyzer (`strict-casts`, `strict-inference`); API design review.

## Naming design seam
**Flow:** consistent vocabulary → positive boolean names (`isEnabled` not `isDisabled`) → imperative verbs for side effects → noun phrases for getters → avoid `get` prefix → prefer private members; export minimal surface.
**Invariant:** positional boolean parameters or one-member abstract class replaceable by function type fails review.
**Probe:** public API audit; `dart analyze` design-related lints.

## Verdict
typed public API, final/const, class modifiers, coherent names, value equality. Learning note: `dart-style-learning-note.md`.
