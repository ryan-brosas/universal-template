<!-- capsule-v2 -->
# Naming — do names reveal entity kind at a glance?

**Source:** Google C++ style guide §Naming. **Question:** Can a reader distinguish types, functions, constants, and members without jumping to declarations?

## Type and function seam
**Path/Symbol:** public C++ identifiers in headers.
**Signature:** PascalCase types and ordinary functions; snake_case variables.
**Data Shape:** `k` prefix for true constants; trailing `_` on class data members only.

### Decisive pattern
```cpp
namespace http_server {

class ConnectionPool {
 public:
  void AddTableEntry();
  int connection_count() const { return connection_count_; }

 private:
  static const int kMaxConnections = 64;
  int connection_count_;
};

struct UrlTableProperties {
  std::string name;
  int num_entries;
};

}  // namespace http_server
```

**Flow:** PascalCase for types/functions → snake_case locals/params → `kMixedCase` compile-time constants → class members end with `_` → struct members plain snake_case → namespaces snake_case.
**Invariant:** `tableName` variables, `table_name` types, or struct fields with trailing `_` fail review.
**Probe:** naming lint / code review checklist; grep for camelCase locals in `.cc` files.

## Descriptive naming seam
**Flow:** names readable to cross-team newcomers → abbreviations only when widely known → file names specific (`http_server_logs.h` not `logs.h`).
**Invariant:** cryptic deletes (`cstmr_id`) or scope-free `kNum` on class members fail review.
**Probe:** new-reader review — can purpose be inferred from name + immediate context?

## Verdict
PascalCase types/functions, snake_case data, kConstant, member trailing underscore. Learning note: `cpp-style-learning-note.md`.
