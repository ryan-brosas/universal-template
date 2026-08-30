<!-- capsule-v2 -->
# BorrowInput + collection GATs — how do validators iterate inputs that may be borrowed or owned?

**Source:** pydantic-core MIT `main@383eb95a19433754c0cecf7025b50c26b6d97a36`; Codebase Memory `pydantic-core`. **Question:** What trait algebra lets one consumer walk a Python list, a JsonArray, and a Mapping without materializing copies?

## A re-borrowing trait over owned-or-borrowed items, GAT views per backend, and an uninhabited `Never` filler
**Path/Symbol:** `src/input/input_abstract.rs:BorrowInput` doc+trait (:185-200), `ValidatedDict/List/Tuple/Set` (:239-279), `ConsumeIterator` (:233-236), `Never` (:283-380); JSON side impls at `src/input/input_json.rs:573-700` (`JsonObject::last_key` :595-597); lifetime erasure at :282-300.
**Signature:** `pub trait BorrowInput<'py> { type Input: Input<'py> + ?Sized; fn borrow_input(&self) -> &Self::Input; }`; `fn iterate<'a, R>(&'a self, consumer: impl ConsumeIterator<ValResult<(Self::Key<'a>, Self::Item<'a>)>, Output = R>) -> ValResult<R>;`
**Data Shape:** each backend names its own Key/Item associated types (JSON: `&str` / `&JsonValue`; Python: Bound Py objects) behind GATs so consumers stay generic.

### Decisive source
```rust
/// The problem to solve here is that iterating collections often returns owned
/// values, but inputs are usually taken by reference. By introducing
/// this trait we abstract over whether the return value from the iterator is owned
/// or borrowed; all we care about is that we can borrow it again with `borrow_input`
/// for some lifetime 'a.
```

**Flow:** validator asks for `input.validate_list(strict)?` → gets backend view → calls `view.iterate(consumer)`; the consumer implements ConsumeIterator once and receives uniform items, re-borrowing each via BorrowInput before child validation. Iterators needing 'static (GenericIterator for iter-validation) clone-and-erase: `GenericIterator::from(a.clone()).into_static()` (input_json.rs:284). The uninhabited `enum Never {}` implements every collection trait with `unreachable!()` so backends lacking a concept (e.g. str has no args) still satisfy the associated-type bounds (:283-380, comment "never actually gets called").
**Invariant:** Consumers never branch on backend; all branching lives in the per-backend view impls. `last_key()` exists on ValidatedDict solely for allow_partial error filtering — keep it when porting the partial contract. JsonObject iteration order = document order (Vec-backed), which is what makes duplicate-key behavior observable downstream.
**Probe:** deterministic source pins this pass: JsonObject::get_item delegates to `key.json_get(self)` (:584-586) tying into the existing lookup-key-alias-resolution capsule; live probe P6 exercised the dict-key path end-to-end ({'[1]': 4} → {(1,): 4}). Direct tests: tests/conftest.py PyAndJsonValidator dual-arm harness (:59-88).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-core", query: "BorrowInput ValidatedDict ConsumeIterator Never", limit: 10 });
// live top-10: one dataclass-test noise row first, then BorrowInput.borrow_input (:192) / ConsumeIterator.consume_iterator (:235) / ValidatedDict trio / Never block — all input_abstract.rs line-exact
```

## Verdict
Adopt: re-borrow abstraction, per-backend view types, single ConsumeIterator consumer, Never-filler pattern for unsupported concepts. Adapt GATs to your generics; omit lifetime-erasure internals if your host GCs for you. Coverage: input_abstract.rs / input_json.rs no_recorded_issue @ gen 2026-08-25T20:09:30Z.
