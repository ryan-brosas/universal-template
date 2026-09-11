<!-- capsule-v2 -->
# Code conventions — are Java/Kotlin files readable and Android-source aligned?

**Source:** ribot §2.1–2.2; xmartlabs §Java. **Question:** Do imports, fields, wrapping, and logging follow team/Android conventions?

## Code seam
**Path/Symbol:** `.java` / `.kt` under `app/src/main`.
**Signature:** no wildcard imports; scoped exceptions; 4-space indent; gated logs.
**Data Shape:** ribot `m`/`s` fields in Java; Kotlin defers to `kotlin-coding-practices`.

### Decisive pattern
```java
public final class SignInActivity extends AppCompatActivity {
    private static final String TAG = SignInActivity.class.getSimpleName();
    private static final String EXTRA_EMAIL = "com.example.extras.EXTRA_EMAIL";

    private EditText mEmailView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        if (BuildConfig.DEBUG) {
            Log.d(TAG, "onCreate");
        }
    }
}
```

**Flow:** never swallow exceptions; catch specific types, not generic `Exception` → avoid finalizers; prefer explicit `close()` patterns → fully qualify imports; no `import foo.*` → Java fields: `m` private instance, `s` private static, constants ALL_CAPS; treat acronyms as words (`XmlHttpRequest`) → indent 4 spaces; wrap long lines at 100 (ribot) or 120 (xmartlabs) using operator-before-break, assignment-after-`=` exception, builder/method-chain line breaks → order imports: android, third-party, java/javax, project; blank line between groups → require `@Override` on overrides; use `@Nullable`/`@NonNull` where applicable → keep local variable scope minimal; declare near first use → define `TAG` for logging; disable verbose/debug on release; never log PII in production → order class members: constants, fields, constructors, lifecycle overrides (lifecycle order for components), public methods, private methods, inner types → method params: `Context` first, callbacks last.
**Invariant:** empty catch, wildcard import, or release `Log.d` with user identifiers fails code convention review.
**Probe:** lint/Checkstyle/detekt; `BuildConfig.DEBUG` log grep; import order check.

## Kotlin seam
**Flow:** new Kotlin modules follow `kotlin-coding-practices` + Android Kotlin style; keep resource/factory rules from other capsules.
**Invariant:** mixing ribot Java `m` prefix into Kotlin public API without project standard fails consistency review.
**Probe:** ktlint/detekt on `.kt` changed files.

## Verdict
Explicit imports, handled exceptions, wrapped long lines, TAG logging gated in release, lifecycle-ordered members. Learning note: `android-style-learning-note.md`.
