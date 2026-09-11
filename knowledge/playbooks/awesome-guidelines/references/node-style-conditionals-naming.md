<!-- capsule-v2 -->
# Conditionals and naming — are identifiers camelCase with strict equality and clear predicates?

**Source:** felixge/node-style-guide §Naming, §Conditionals, §Variables. **Question:** Do names, ===, and object literals match felixge Node conventions?

## Naming seam
**Path/Symbol:** identifiers in Node `.js` sources.
**Signature:** lowerCamelCase vars/functions; UpperCamelCase classes; UPPERCASE constants.
**Data Shape:** descriptive names; no snake_case.

### Decisive pattern
```js
const SECOND = 1 * 1000;

function BankAccount() {
}

var isValidPassword =
  password.length >= 4 && /^(?=.*\d).{4,}$/.test(password);

if (isValidPassword) {
  saveUser();
}
```

**Flow:** variables, properties, functions → **lowerCamelCase** → classes → **UpperCamelCase** → constants → **UPPERCASE** (prefer `const SECOND = …` in modern code over felixge `var`) → use **=== / !==** never loose equality → split **multi-line ternary** across lines → assign **non-trivial conditions** to descriptively named booleans before `if` → object/array literals: trailing commas OK; keep short literals on one line; quote keys only when required.
**Invariant:** snake_case, `==`, or inline regex soup in `if` without named predicate fails Node naming/conditional review.
**Probe:** grep `\bvar [a-z]+_[a-z]`; `==` without `===` context; complex if conditions without named vars.

## Verdict
camelCase + strict equality + descriptive condition variables + tidy literals. Learning note: `node-style-learning-note.md`.
