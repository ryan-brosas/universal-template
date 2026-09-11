<!-- capsule-v2 -->
# Ownership and RAII — is heap ownership explicit and lifetimes safe?

**Source:** Google C++ §Ownership and Smart Pointers; C++ Core Guidelines R.* / F.*. **Question:** Are owners, borrowers, and transfers obvious at call sites?

## Ownership seam
**Path/Symbol:** APIs returning or receiving heap resources.
**Signature:** `std::unique_ptr` for exclusive ownership; raw pointers non-owning.
**Data Shape:** move transfers ownership; `shared_ptr` only when sharing is intentional.

### Decisive pattern
```cpp
std::unique_ptr<Foo> FooFactory();
void FooConsumer(std::unique_ptr<Foo> foo);

void UseBorrowed(const Foo& foo);  // non-owning
void MaybeNull(Foo* foo);          // nullable borrow — document lifetime
```

**Flow:** allocate → immediately hand to manager object → transfer with `unique_ptr` move → share with `shared_ptr` only when required → never `new`/`delete` naked in application code.
**Invariant:** raw pointer parameters implying ownership transfer without smart pointer type fail review.
**Probe:** clang-tidy checks (`modernize-make-unique`, `clang-analyzer-cplusplus.NewDelete`); no naked `new` in diff.

## RAII seam
```cpp
void ProcessFile(absl::string_view path) {
  std::ifstream input{std::string(path)};
  // lock guards, unique_ptr, containers — scope ends release
}
```

**Flow:** resource handles (files, locks, memory) tied to scope → prefer return values over out-parameters → do not return pointer/reference to local.
**Invariant:** manual `delete`, `free`, or out-param heap writes in new code fail review.
**Probe:** static analysis + code search for `new ` / `delete ` in changed lines.

## Verdict
unique_ptr transfer, non-owning raw refs, RAII, return over out-params. Learning note: `cpp-style-learning-note.md`.
