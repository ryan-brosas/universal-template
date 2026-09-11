<!-- capsule-v2 -->
# PKCE + state generation — the crypto helpers and the comment-vs-code divergence you must not "fix" blindly

**Source:** bruno MIT `main@675965612ff11b23bc9b6c9541110a287bcb2967`; Codebase Memory `ext-bruno`. **Question:** How are PKCE verifier/challenge and the anti-CSRF state actually generated — and what does the code do when a user supplies their own state?

## Connected graph-selected seam
**Path/Symbol:** `packages/bruno-electron/src/utils/oauth2.js:generateCodeVerifier` (:711-713), `generateState` (:718-725), `generateCodeChallenge` (:727-735); call sites in `getOAuth2AuthorizationCode`.
**Signature:** `generateCodeVerifier() → string; generateState({userState}) → string; generateCodeChallenge(codeVerifier) → string`.
**Data Shape:** verifier = 22 random bytes hex (44 chars, RFC 7636 range); challenge = base64url(SHA-256(verifier)) with `+→-`, `/→_`, `=` stripped.

### Decisive source
```js
// Build an OAuth2 state string to help prevent CSRF and forged auth codes.
// If the user passes a state, it goes first; we append random bytes after it.
const generateState = ({ userState }) => {
  const trimmedUserState = userState?.trim();
  if (trimmedUserState && trimmedUserState.length > 0) {
    return trimmedUserState;
  }
  let cryptographicallyRandomString = crypto.randomBytes(16).toString('hex');
  return cryptographicallyRandomString;
};
```

**Flow:** authorization-code flow generates a FRESH verifier+challenge per attempt (not per collection), builds the authorize URL with `code_challenge_method=S256`, issues `effectiveState = generateState({userState: state})`, passes it as `expectedState` to the authorize window/protocol handler which fail-closes on mismatch. Implicit flow issues state the same way (no PKCE).
**Invariant:** THE TRAP — the comment above `generateState` claims user state gets random bytes APPENDED ("it goes first; we append random bytes after it") but the CODE returns the user's state verbatim with NO suffix; a random suffix would break servers that echo-check exact state, and a porter who "fixes" code to match comment (or vice versa) must know the shipped behavior is verbatim-return + separate random-only-when-absent. The validation half is strict equality against `expectedState`; missing expected OR returned state rejects.
**Probe:** `packages/bruno-tests/src/auth/oauth2/authorizationCode.js` :20-25 (`generateCodeChallenge` pins S256 base64url shape end-to-end).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-bruno", query: "generateCodeChallenge generateState", limit: 5 });
// resolves electron twins :727-735 / :718-725 line-exact
```

## Verdict
Adopt fresh-per-attempt PKCE with standard base64url SHA-256 challenge and random-when-absent state with strict-equality validation. Adapt byte lengths to your RFC tolerance; omit Bruno's debug envelope. Coverage caveat: comment/code divergence recorded here so future passes do not "correct" either side silently.
