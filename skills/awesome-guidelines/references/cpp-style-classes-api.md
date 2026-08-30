<!-- capsule-v2 -->
# Classes and API surface — are types safe to construct and use?

**Source:** Google C++ §Classes, §Functions; Core Guidelines C.* / F.*. **Question:** Do classes avoid half-initialized states and surprise conversions?

## Constructor seam
**Path/Symbol:** class constructors and conversion operators.
**Signature:** no virtual calls in ctors; `explicit` single-argument ctors.
**Data Shape:** factory or `Init()` only when failure signaling requires it.

### Decisive pattern
```cpp
class Timer {
 public:
  explicit Timer(int interval_ms);
  Timer(const Timer&) = delete;
  Timer& operator=(const Timer&) = delete;

  void Start();
 private:
  int interval_ms_;
};

// Passive data — prefer struct
struct Endpoint {
  std::string host;
  int port;
};
```

**Flow:** keep ctors simple → never call virtual methods from ctor → mark narrowing ctors `explicit` → use struct for aggregates → delete/copy control when ownership-sensitive.
**Invariant:** virtual dispatch in constructor or implicit conversion ctor without `explicit` fails review.
**Probe:** grep `virtual` callees from ctor bodies; clang-tidy `google-explicit-constructor`.

## Function seam
```cpp
absl::StatusOr<Table> LoadTable(absl::string_view name);

void RotateShape(Shape& shape, double radians);
```

**Flow:** short functions, one logical operation → prefer return values (`StatusOr`, struct) over out-parameters → const-correct inputs → unnamed params only when type makes role obvious.
**Invariant:** multi-hundred-line functions or bool `IsValid()` half-constructed objects in new code fail review.
**Probe:** function length lint; API review for out-params replaceable by returns.

## Verdict
No virtual-in-ctor, explicit conversions, struct for data, short const-correct APIs. Learning note: `cpp-style-learning-note.md`.
