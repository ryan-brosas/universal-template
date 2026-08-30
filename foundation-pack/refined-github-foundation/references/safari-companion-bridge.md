<!-- capsule-v2 -->
# Safari companion bridge — how does a macOS/iOS container app drive a Safari Web Extension's enabled state and settings without any shared code?

**Source:** refined-github MIT `main@3bbe6088fe301d0d5cf1ae751a49307005762a68`; Codebase Memory `refined-github`. **Question:** When shipping a browser extension that needs a native container (Safari requires one), what is the minimal bridge pattern between the SwiftUI shell and the extension, and which platform APIs differ across macOS/iOS?

## Platform-split SafariExtension facade over SFSafariExtensionManager
**Path/Symbol:** `safari/Refined GitHub/Utilities.swift:SafariExtension` (:5–25); consumer `safari/Refined GitHub/MainScreen.swift:MainScreen` (:121–159); bundle id in `Constants.swift`.
**Signature:** `static func isEnabled(forIdentifier identifier: String) async throws -> Bool`; `static func openSettings(forIdentifier identifier: String) async throws`.
**Data Shape:** Two async throwing class functions; all call sites funnel through them so OS differences live in ONE file. Index caveat: MainScreen.swift is parse_partial for ranges 5–141 + 172; every cited range here (:100–171) was read from raw source, outside flagged lines.

### Decisive source
```swift
// Utilities.swift — the whole portability seam
#if os(macOS)
static func isEnabled(forIdentifier identifier: String) async throws -> Bool {
	try await SFSafariExtensionManager.stateOfSafariExtension(withIdentifier: identifier).isEnabled
}
#else
@available(iOS 26.2, visionOS 26.2, *)
static func isEnabled(forIdentifier identifier: String) async throws -> Bool {
	try await SFSafariExtensionManager.stateOfExtension(withIdentifier: identifier).isEnabled   // note: no "Safari" infix
}
#endif
```

**Flow:** App launch/scene-activation → `updateExtensionStatus()` queries enabled state via the facade → UI shows ✓ Enabled / ✗ Disabled → buttons call `openSettings` (`SFSafariApplication.showPreferencesForExtension` on macOS — then `NSApplication.shared.terminate(nil)` because opening settings ends the utility app's life; `SFSafariSettings.openExtensionsSettings(forIdentifiers:)` on iOS 26.2+). Older iOS falls back to a `x-safari-https://` deep-link "Get Started" page.
**Invariant:** The app "is just a container for the Safari extension and does not do anything" (its own footer copy): NO data or messages flow between app and extension at runtime — the bridge is only these two reflective state/settings calls keyed by `Constants.extensionBundleIdentifier`. Status must be re-checked on every `scenePhase == .active`, not cached: the user can toggle the extension in Settings at any time.
**Probe:** No Swift unit tests exist (UI-bound, Xcode-only build); coverage caveat recorded — contract pinned by source read of both files plus parse_partial range exclusion check.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "SafariExtension isEnabled", limit: 10 });
// graph holds partial Swift symbols; ranges above verified against raw file
```

## Verdict
Adopt the facade shape (one enum exposing `isEnabled`/`openSettings`, `#if os(macOS)` split inside, single bundle-id constant) for any Safari Web Extension container app; adopt the terminate-after-open-settings macOS behavior and re-check-on-activate status loop. Adapt availability gating (`@available(iOS 26.2, …)`) and the pre-26 fallback link to your deployment floor. Omit StoreKit review-prompt plumbing (`requestReviewIfNeeded`) — product surface, not bridge mechanics.
