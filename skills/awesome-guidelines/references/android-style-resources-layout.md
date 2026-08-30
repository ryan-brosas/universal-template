<!-- capsule-v2 -->
# Resources and layout — do filenames and ids follow Android prefix rules?

**Source:** ribot §1.2, §2.3; xmartlabs §Resources. **Question:** Can designers and devs predict drawable, layout, and id names from component types?

## Resource seam
**Path/Symbol:** `res/drawable`, `res/layout`, `res/values`, `res/menu`.
**Signature:** lowercase_underscore files; typed prefixes; self-closing empty tags.
**Data Shape:** `activity_sign_in.xml`; `ic_star.png`; `@+id/text_title`.

### Decisive pattern
```xml
<!-- res/layout/activity_sign_in.xml -->
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent">

    <TextView
        android:id="@+id/text_email_hint"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="@string/registration_email_hint" />

</LinearLayout>
```

**Flow:** name component classes UpperCamelCase with Android suffix (`SignInActivity`, `ChangePasswordDialog`) → match layout/menu files: `activity_sign_in.xml`, `fragment_sign_up.xml`, `dialog_change_password.xml`, adapter rows `item_person.xml`, partials `partial_*` → prefix drawables (`ic_`, `btn_`, `tab_`, state suffix `_pressed/_disabled`) → keep values files plural (`strings.xml`, `colors.xml`) → prefix string keys by section (`registration_email_hint`; `error_*`, `title_*`, `action_*` when global) → put string arrays in separate file; array items reference `@string/…` resources, not literals → use self-closing tags for empty elements → order layout attributes: namespaces first (android, app, tools alphabetically), then id, width/height, remaining attrs alphabetically; single blank line before closing root tag (xmartlabs) → style names UpperCamelCase; reuse styles only when shared.
**Invariant:** layout filename mismatch with component, unprefixed drawable (`logo.png`), or literal strings inside `<string-array>` fail resource review.
**Probe:** lint resource naming; layout↔Activity name crosswalk; string-array item reference check.

## Id naming seam
**Flow:** snake_case ids with element/context prefixes (`text_`, `image_`, `button_`, or `customer_list_description_textView` pattern).
**Invariant:** generic `@+id/title` without context prefix fails id review on large screens.
**Probe:** layout id prefix spot check.

## Verdict
Prefixed lowercase_underscore resources, component-aligned layouts, referenced string arrays, ordered XML attrs. Learning note: `android-style-learning-note.md`.
