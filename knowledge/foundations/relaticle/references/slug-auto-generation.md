<!-- capsule-v2 -->
# Slug auto-generation ownership — how do you auto-generate a unique handle until the user edits it, with a CJK-safe fallback?

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; Codebase Memory `relaticle`. **Question:** A name→slug field pair must regenerate while "untouched" and freeze once the user takes ownership — what state machine tracks that, and what happens when Str::slug transliterates to nothing?

## Hidden slug_auto_generated flag + transliteration fallback
**Path/Symbol:** `app/Filament/Pages/CreateTeam.php` :430-465 (name/slug/hidden trio), :398 `generateHandleFrom(?string $name): string`.
**Signature:** `afterStateUpdated` closures over Filament `Get`/`Set`; hidden flag `slug_auto_generated` defaults true, dehydrated false (never persisted — pure UI state).
**Data Shape:** slug validated by `ValidTeamSlug` rule + `unique(table: Team::class, ignorable: current tenant)`; UI prefix `"{appHost}/"` shows the handle's full URL.

### Decisive source
```php
if ($get('slug_auto_generated') !== true && filled($get('slug'))) {
    return;
}

$set('slug', $this->generateHandleFrom($state));
$set('slug_auto_generated', true);
```
(:438-443 name-side) and the slug-side reset (:459-461 `$set('slug_auto_generated', false)` on ANY user edit of slug). Fallback:
```php
$slug = Str::slug($name);

return $slug === '' ? Str::lower(Str::random(8)) : $slug;
```
(:404-406). Docblock: mirrors the fallback in Team::getSlugOptions() — names that transliterate to nothing (CJK, Hebrew, Thai, emoji) otherwise leave the handle blank and the user is blocked by a bare "required" error on a field they never touched. The guard condition is deliberately two-clause: an empty-but-user-owned slug (`filled` fails) is left alone.

**Flow:** mount: flag=true → user types name ⇒ flag still true ⇒ regenerate slug + keep flag true → user edits slug directly ⇒ flag=false → further name edits no longer overwrite (flag≠true OR slug filled) → submit validates rule+uniqueness regardless.
**Invariant:** Exactly ONE writer owns the slug at a time, arbitrated by the flag; regeneration must never fight manual edits, and the fallback must exist in BOTH the form and the model layer or the two disagree for non-Latin names.
**Probe:** `tests/Feature/Onboarding/CreateTeamOnboardingTest.php` (:182 custom-slug respected; :203/:218 slug format/uniqueness validation; :824 generates-a-fallback-handle-for-names-that-transliterate-to-nothing).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "generateHandleFrom slug_auto_generated ValidTeamSlug afterStateUpdated", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the flag-arbitrated dual-writer pattern and the random-fallback-on-empty-transliteration; adapt validators to your stack; omit Filament specifics. Three direct tests pin custom-slug respect and the CJK fallback.
