<!-- capsule-v2 -->
# formula-support-validator-family-vetoes — Which AST detector families veto a generated column, and what does each catch?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What are the six detector passes inside FormulaSupportGeneratedColumnValidator beyond function support?

## DatetimeConcat / DatetimeTextSlice / LogicalNonBool / NumericFnNonNumeric / LogicalFunctions detectors + TypeInferVisitor
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/formula-support-generated-column-validator.ts` — pipeline :60-86; TypeInferVisitor :398-529; InvalidArithmeticDetector :530-600; DatetimeConcatDetector :601-654; DatetimeTextSliceDetector :655-698; LogicalArgumentDetector :699-763; NumericFunctionArgDetector :764-800; LogicalFunctionDetector :801+.
**Signature:** each detector extends AbstractParseTreeVisitor<boolean> walking the parsed formula AST.
**Data Shape:** TypeInferVisitor classifies literals/fields/operators into string|number|boolean|datetime|unknown with CONSERVATIVE '+' (any string/datetime side ⇒ string result) and arithmetic requiring numeric operands.

### Decisive source
```ts
if (this.hasDatetimeStringConcatenation(tree)) return false;
if (this.hasDatetimeTextSlicing(tree)) return false;
if (this.hasLogicalNonBooleanArgs(tree)) return false;
if (this.hasNumericFunctionWithNonNumericArgs(tree)) return false;
if (this.containsLogicalFunctions(tree)) return false;
```

**Flow:** parse → field-reference family veto (links/lookups/system fields/nested non-persisted formulas) → datetime concat veto (datetime + '&' or string '+' would embed mutable formatting) → text slicing of datetimes (LEFT/RIGHT on dates) → AND/OR/IF with non-boolean args → numeric functions over text args → ISERROR/ERROR/BLANK-style logical fns outright → per-function support check → type-safety pass via TypeInferVisitor.
**Invariant:** vetoes are ordered cheapest-first and ALL must pass — the validator is a pure predicate (boolean, warn-on-parse-error) with no partial output, so an unsupported formula simply stays virtual. Upstream spec pins three behaviors: numeric-over-text rejected, numeric pair allowed, TEXTBEFORE/TEXTSPLIT rejected.
**Probe:** upstream direct spec `formula-support-generated-column-validator.spec.ts:12-70`; static byte-exact: `grep -n 'hasDatetimeStringConcatenation\|hasLogicalNonBooleanArgs' formula-support-generated-column-validator.ts | head -4`.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"validateFormula","limit":3,"detail":"ids"}'
```

## Verdict
Adopt the detector-pipeline shape for any pre-DDL formula gate. Adapt veto list to your dialect's immutable subset. Omit nothing.
