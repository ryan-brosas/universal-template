<!-- capsule-v2 -->
# Architecture and verification — is UI separated from data with lint-clean builds?

**Source:** ribot architecture_guidelines; ribot README Jetpack pointer. **Question:** Are view, presentation, and data responsibilities separated and verified in CI?

## Architecture seam
**Path/Symbol:** app module packages (`ui`, `presenter`/`viewmodel`, `data`).
**Signature:** View handles UI/lifecycle; presenter/viewmodel maps data; data layer owns IO.
**Data Shape:** helpers + DataManager (ribot) → Repository pattern (Jetpack).

### Decisive pattern
```
View (Activity/Fragment/Compose)
    ↕ user events / render calls
Presenter or ViewModel
    ↕ observables / suspend flows
DataManager / Repository
    ↕
Helpers (API, DB, Preferences)
```

**Flow:** keep UI components (Activities/Fragments/Compose) in view layer — forward user input upward; render from presentation layer callbacks → presentation layer subscribes to data streams; no direct SQL/HTTP in views → data layer splits focused helpers (API, DB, prefs) composed by DataManager/Repository; return domain models, not UI-formatted strings → use event bus only for cross-screen broadcast (e.g., signed out), not routine screen logic → greenfield: map MVP roles to Jetpack (ViewModel, Repository, Room/DataStore, Navigation) per ribot maintenance note → verify with Android Gradle structure; run lint/detekt/ktlint and unit/instrumented tests on changed modules → gate debug logs and PII as in code conventions capsule.
**Invariant:** Activity performing Retrofit/SQLite directly, or presenter holding View context beyond lifecycle, fails architecture review.
**Probe:** package dependency scan (view must not import retrofit/room directly); lint/detekt CI exit 0.

## Verify seam
**Flow:** `./gradlew lint`, unit tests, Espresso on touched flows; optional PSScriptAnalyzer N/A — use Android lint rulesets.
**Invariant:** PR touching UI without test delta on critical path fails verify gate when project requires it.
**Probe:** Gradle lint/test artifacts on changed module.

## Verdict
Layered MVP/Jetpack mapping, narrow helpers, broadcast-only event bus, lint+tests on app changes. Learning note: `android-style-learning-note.md`.
