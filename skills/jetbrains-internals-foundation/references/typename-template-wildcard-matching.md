<!-- capsule-v2 -->
# TypeNameTemplate structured wildcard matching — how do debugger type-name patterns match templated C++ names without regex blowup?

**Source:** JetBrains Rider installed build `RD-262.8665.400` (`plugins/cidr-debugger-plugin/bin/helpers/jb_declarative_formatters/type_name_template.py`, 82L whole); Codebase Memory `jetbrains-rider`. **Question:** How should `std::vector<*>`-style visualizer patterns match concrete template instantiations, including variadic trailing wildcards, while reporting WHICH arguments matched?

## match() as the decisive instance
**Path/Symbol:** `type_name_template.py:TypeNameTemplate.match` (:51-82), `is_wildcard` (:47-49), `has_wildcard` (:36-45).
**Signature:** `match(candidate: TypeNameTemplate, out_matched_args: list[TypeNameTemplate] | None) -> bool`.
**Data Shape:** node = {name, fmt, args[], original_text}; wildcard is the literal name '*'; fmt+args round-trip via `fmt.format(*args)`.

### Decisive source
```python
# Handle special case:
# trying to match type
#   T<..., A, B, ...>
# to template type
#   T<..., *>
# We need to properly match A, B, ... types as out_matched args for single wildcard
if args_count < candidate_args_count:
    # if last template arg is not wildcard
    if args_count == 0 or not self.args[-1].is_wildcard:
        return False
    if out_matched_args is not None:
        out_matched_args.extend(candidate.args[args_count:])
return True
```

**Flow:** root '*' matches anything and captures the WHOLE candidate → otherwise names must equal, then pattern args zip prefix-wise against candidate args with recursion → surplus candidate args are legal ONLY when the pattern's LAST arg is the wildcard, which absorbs all of them into out_matched_args in order.
**Invariant:** arity rule: pattern may be SHORTER than candidate only via trailing wildcard; longer-than-candidate always fails. Wildcard detection is structural (`has_wildcard` recurses through args), never string scanning of formatted names. Wrong port: converting templates to regex strings first — nested angle brackets and the '> >' spacing convention make string matching wrong; the structured walk also gives you matched-argument bindings for free (needed to instantiate viz expressions like std::vector<T>'s value-type nodes).
**Probe:** executed GREEN against the shipped module loaded file-directly: wildcard-root match captures ['std::vector<int>']; T<*> vs T<A,B,C> captures ['A','B','C']; arity mismatch fails; name mismatch fails; has_wildcard propagates through nesting; str round-trip Outer<Inner<*>>.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-rider", name_pattern: ".*TypeNameTemplate.*", limit: 6 });
// -> ...type_name_template.TypeNameTemplate Class 6-82
```

## Verdict
Adopt the structured-walk matcher wherever declarative patterns bind against parameterized names (debugger viz, formatter rules, serializer registries); the captured-args output is the design's real payoff. Adapt the grammar tokens. Omit the C++-specific fmt handling if your names are simple. Companion fact from the same plane: TypeVizTopLevelMethods substitutes $T<i> markers as ${DECLARATION_CONTEXT_WILDCARD_i} WITH a trailing space because its Clang-based parser cannot handle '>>'.