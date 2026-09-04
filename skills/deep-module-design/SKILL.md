---
name: deep-module-design
description: "Use when reviewing module boundaries, designing a deep module, reducing interface complexity, or reviewing AI-generated code for structural quality. Hidden by default: load for explicit design-review requests."
invocation: manual
disable-model-invocation: true
---


# Deep Module Design

## Core Principle

Interface is the design, push complexity down, expose simplicity up; small interface, deep implementation.

## Design rules (heuristics, not laws)

- **Interface is the design.** What the module *exposes* is what it is.
- **Hide complexity behind the interface.** Callers should not read internals to use it.
- **Push complexity down, expose simplicity up.**
- **One concept per module.** Two things = two interfaces pretending to be one.
- **Small interface, deep implementation.**

These are decision hints to weigh, not universal gates; a shallow helper with two callers can be the right shape.

## When to Use

Designing a new module; reviewing structure; refactoring shallow modules; "this class is too big"; API of a new library; service boundary.

## When NOT to Use

Trivial one-function helpers; structure is fine and change is in body; "design" without a real module.

## Workflow

1. Measure depth: impl size / interface size.
2. Read the interface tells and design tells tables.
3. Refactor toward depth: find the shallowest surface, combine methods, hide helpers, move config inside, return less.
4. Test the interface, not internals, if a test mocks an internal call, the internal is leaking.

## The Depth Metric

```
Depth = (impl size) / (interface size)
```

- **Deep**: small interface, large impl. Good. Hides complexity.
- **Shallow**: large interface, small impl. Bad. Exposes its guts.

10 public methods, 50-line constructor = shallow. 1 public method, 1000 lines = deep (if it solves a real problem).

## Interface Tells

| Sign | Meaning |
|---------------------------------|-----------------------------|
| Many public methods | Module is doing too much |
| Methods with complex args | Caller knows too much |
| Methods returning complex types | Caller handles too much |
| Public state | Caller can break invariants |
| Config that requires docs | Hide defaults |
| `addX`/`addY`/`addZ` | One method, options |

## Design Tells

| Sign | Meaning |
|---------------------------|-----------------------------|
| Impl bigger than expected | Caller reads the impl |
| Two ways to do the same | Pick one, hide the other |
| Caller calls 3+ methods | One method, the right thing |
| "Don't call from outside" | Should be private |
| Tests mock internals | Internals leaking |

## Refactoring Toward Depth

1. **Find shallowest surface.** List public methods + args.
2. **Combine methods.** `addUser + addUserAddress` → `addUser({ ..., address })`.
3. **Hide the helper.** Make internal calls private.
4. **Move config inside.** Env, sensible default. Not per-call args.
5. **Return less.** `{ ok, data, error, meta }` → `data`. Errors at boundary.

## Test Seams via Interface

The interface IS the test seam. Test the interface, not the implementation. If your test needs to mock an internal call, the internal is leaking.

```ts
// GOOD: test the interface
const svc = new UserService({ db: mockDb, mailer: mockMailer })
await svc.addUser({ name, email })
expect(mockDb.users).toContain(...)

// BAD: test the internals
jest.spyOn(svc, "_insertIntoDb")
jest.spyOn(svc, "_sendEmail")
```

## Common Mistakes

Shallow modules; exposed state; config in args (env); "two ways to do it"; tests mock internals; `addX`/`addY`/`addZ`; "don't call from outside" comments; pass-through modules.

## Red Flags

10+ public methods; `addX`/`addY`/`addZ`; public state; config in args; "don't call from outside"; tests mock internals; pass-through; "two ways to do it"; 3+ methods in sequence.

## Anti-Patterns

**Shallow module**; **public state**; **config in args**; **two ways to do it**; **tests mock internals**; **addX/addY/addZ**; **pass-through**; **complex return types**.

## Verification

Depth improved (smaller interface, larger impl); no public state; config moved inside with sensible defaults; tests exercise the interface, not mocked internals; one way to do each thing.


## References

N/A, no reference files; this skill is self-contained.
