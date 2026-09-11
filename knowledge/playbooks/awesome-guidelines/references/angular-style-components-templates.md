<!-- capsule-v2 -->
# Components and templates — do classes use inject, readonly signals, and simple templates?

**Source:** Angular Style Guide §Dependency injection, §Components and directives. **Question:** Are components presentation-focused with modern Angular member and template patterns?

## DI seam
**Path/Symbol:** Angular components, directives, services.
**Signature:** inject(); Angular APIs before methods; protected/readonly members.
**Data Shape:** `readonly userId = input();` `protected fullName = computed(...)`.

### Decisive pattern
```typescript
@Component({
  template: `<button (click)="saveUserData()">Save</button>
             <p>{{ fullName() }}</p>`,
})
export class UserProfile implements OnInit {
  private readonly api = inject(UserApi);

  readonly userId = input.required<string>();
  readonly userSaved = output<void>();

  firstName = input('');
  protected fullName = computed(() => `${this.firstName()} …`);

  ngOnInit() {
    this.startLogging();
  }

  protected saveUserData() { /* … */ }
  private startLogging() { /* … */ }
}
```

**Flow:** prefer **`inject()`** over constructor parameter injection → group **injected deps, inputs, outputs, queries** before **methods** → keep components **presentation-focused** — move decoupled logic to **services/functions** → refactor **complex template** logic to **computed**/TS → template-only members **`protected`** → Angular-initialized props **`readonly`** (`input`, `model`, `output`, queries) → use **`[class]`/`[style]`** bindings instead of **`ngClass`/`ngStyle`** → name handlers for **action** (`saveUserData`) not **`handleClick`** → lifecycle hooks **thin** — delegate to named methods → **implement lifecycle interfaces** (`implements OnInit`).
**Invariant:** heavy ngOnInit body, public template-only member, or ngClass for trivial class toggle fails component review.
**Probe:** eslint @angular-eslint rules; spot-check template complexity.

## Verdict
inject-based DI, ordered signal APIs, protected/readonly members, simple templates, semantic handlers. Learning note: `angular-style-learning-note.md`.
