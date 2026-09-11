<!-- capsule-v2 -->
# Selectors and verify — do selectors, inputs/outputs, and lint gates follow Angular docs?

**Source:** Angular Style Guide + Components selectors/inputs/outputs guides. **Question:** Are custom elements, I/O names, and CI checks aligned with angular.dev?

## Selector seam
**Path/Symbol:** `@Component`/`@Directive` selectors, template bindings.
**Signature:** hyphenated custom elements with app prefix; camelCase outputs.
**Data Shape:** `yt-menu` element; `[mrTooltip]` attribute directive.

### Decisive pattern
```typescript
@Component({
  selector: 'mr-film-details',
  …
})
export class FilmDetails {
  readonly filmId = input.required<string>();
  readonly saved = output<void>(); // not onSaved
}
```

**Flow:** components: **custom element** selector with **hyphen** per HTML spec → use **short app prefix** on all custom components (`mr-film-details`) — **never `ng` prefix** → attribute directives: **camelCase** attribute with app prefix (`[mrTooltip]`) → use attribute selector when wrapping native elements (e.g. button) → **inputs/outputs**: avoid names that **collide with DOM** properties → **no prefix** on input/output names like selectors → outputs: **camelCase**, **no `on` prefix** → verify with **@angular-eslint** + **`ng build`** / **`ng test`** on changed projects.
**Invariant:** selector without hyphen, `ng-` app prefix, or output named `onSave` fails selector/I/O review.
**Probe:** eslint component-selector rule; grep `@Output.*on[A-Z]`.

## Verify seam
**Flow:** run **angular-eslint** on changed TS/HTML → **unit tests** colocated `*.spec.ts` pass → **typecheck** strict templates → cross-check **typescript-coding-standards** for non-Angular TS → manual: feature folder placement, `main.ts` bootstrap, readonly inputs.
**Probe:**
```bash
ng lint
ng test --include='**/film-details/**'
```

## Verdict
Prefixed hyphen selectors, safe I/O names, angular-eslint + test verify on changed feature code. Learning note: `angular-style-learning-note.md`.
