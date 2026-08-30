<!-- capsule-v2 -->
# Components and tests — are navigation args and tests factory-driven?

**Source:** ribot §2.2.13–2.2.15, §2.4; xmartlabs §Fragments and Activities. **Question:** Do Activities/Fragments expose typed entry points and consistent test names?

## Component seam
**Path/Symbol:** Activities, Fragments, instrumented/unit tests.
**Signature:** `getStartIntent` / `newInstance`; private prefixed keys; lifecycle factories before `onCreate`.
**Data Shape:** `PREF_`/`EXTRA_`/`ARGUMENT_` key constants; `FooTest` / `FooActivityTest`.

### Decisive pattern
```java
public final class UserActivity extends AppCompatActivity {
    private static final String EXTRA_USER = "com.example.extras.EXTRA_USER";

    public static Intent getStartIntent(Context context, User user) {
        Intent intent = new Intent(context, UserActivity.class);
        intent.putExtra(EXTRA_USER, user);
        return intent;
    }
}

public final class UserFragment extends Fragment {
    private static final String ARGUMENT_USER = "ARGUMENT_USER";

    public static UserFragment newInstance(User user) {
        UserFragment fragment = new UserFragment();
        Bundle args = new Bundle();
        args.putParcelable(ARGUMENT_USER, user);
        fragment.setArguments(args);
        return fragment;
    }
}
```

**Flow:** prefix Intent/Bundle/SharedPreferences keys (`PREF_`, `BUNDLE_`, `ARGUMENT_`, `EXTRA_`, `ACTION_`); use full package for Intent actions/extras when required → provide `public static getStartIntent(Context, …)` on Activities and `newInstance(…)` on Fragments; place factories before `onCreate`; keep keys private when factories exist → name fragments/activities after use case + suffix (`CustomerListFragment`, `RepoDetailActivity`); ViewPager pages may use `PageFragment` suffix (xmartlabs) → unit tests named `ClassUnderTestTest`; methods `@Test void methodPreconditionExpectedBehaviour()` → split large test classes by feature area → Espresso tests named `ActivityTest`; put each chained matcher/call on its own line.
**Invariant:** Activity started with raw string extras, missing factory method, or public `EXTRA_*` constant without encapsulation fails component review.
**Probe:** factory-method presence audit; Espresso chain formatting spot check.

## Naming seam
**Flow:** list screens use singular entity in class name (`CustomerListFragment`, not `CustomersListFragment`).
**Invariant:** plural entity in fragment class name for single-entity list fails xmartlabs naming review.
**Probe:** `*ListFragment` / `*DetailActivity` name walk.

## Verdict
Factory-based navigation, prefixed private keys, structured test naming, Espresso one-call-per-line. Learning note: `android-style-learning-note.md`.
