<!-- capsule-v2 -->
# Naming and files — do kebab-case filenames, specs, and component triplets match Angular 2025 rules?

**Source:** Angular Style Guide §Naming. **Question:** Do file names mirror TypeScript identifiers and colocate component assets?

## File seam
**Path/Symbol:** Angular `src/` TypeScript, HTML, CSS files.
**Signature:** kebab-case stems; `.spec.ts` beside source; shared component base name.
**Data Shape:** `user-profile.ts`, `user-profile.html`, `user-profile.css`, `user-profile.spec.ts`.

### Decisive pattern
```
show-times/film-details/
  film-details.ts
  film-details.html
  film-details.css
  film-details.spec.ts
```

**Flow:** separate words in filenames with **hyphens** → filename reflects primary **class name** (`UserProfile` → `user-profile.ts`) → unit tests: same stem + **`.spec.ts`** colocated → component **ts/html/css** share **same base name** → extra style files: append descriptor (`user-profile-settings.css`) → avoid generic **`helpers.ts`/`utils.ts`/`common.ts`** dumping grounds → when file-local style contradicts guide, **prefer file consistency** (guide introduction).
**Invariant:** PascalCase source filename, distant test folder, or mismatched component stem fails naming review.
**Probe:** list changed feature dir; verify spec adjacent; grep `utils\.ts` growth.

## Verdict
Kebab-case mirrored filenames, colocated specs, aligned component asset stems. Learning note: `angular-style-learning-note.md`.
