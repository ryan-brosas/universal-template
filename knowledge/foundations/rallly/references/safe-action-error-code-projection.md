<!-- capsule-v2 -->
# Safe-action error-code projection — how does the client turn untyped string server codes into localized feedback without leaking unknown codes as crashes?

**Source:** Rallly AGPL-3.0 `main@1b085700afec1dd5aa0eca419133dcba9bcdc9d6`; Codebase Memory `rallly`. **Question:** What single client hook wraps every next-safe-action call, and what are its two unconditional behaviors?

## useSafeAction wrapper — always refresh, always toast known codes
**Path/Symbol:** `apps/web/src/lib/safe-action/client.ts:useSafeAction` (whole file, 72L); producer side `apps/web/src/lib/safe-action/server.ts:handleServerError` (see `safe-action-procedure-ladder`).
**Signature:** `useSafeAction: typeof useAction` — a drop-in typed wrapper around `next-safe-action/hooks`' `useAction`.
**Data Shape:** `error.serverError` is an untyped string; the hook casts it to `AppErrorCode` and switches over the known set (UNAUTHORIZED, NOT_FOUND, FORBIDDEN, INTERNAL_SERVER_ERROR, TOO_MANY_REQUESTS, PAYMENT_REQUIRED, SERVICE_UNAVAILABLE, PAYLOAD_TOO_LARGE).

### Decisive source
```ts
return useAction(action, {
  ...options,
  onSuccess: (args) => {
    router.refresh();
    options?.onSuccess?.(args);
  },
  onError: (args) => {
    const { error } = args;
    if (error.serverError) {
      let translatedDescription = "An unexpected error occurred";
      switch (error.serverError as AppErrorCode) {
        case "UNAUTHORIZED": translatedDescription = t("actionErrorUnauthorized", {...}); break;
        // ... one case per known code ...
      }
      toast.error(translatedDescription);
    }
    options?.onError?.(args);
  },
});
```

**Flow:** every action success triggers `router.refresh()` BEFORE delegating to the caller's onSuccess (server actions mutate data the current page may be rendering — refresh keeps it coherent; callers then do their own cache patching like `poll-mute-owner-scoped-toggle`) → on error, an unknown/missing code falls through the switch into the generic message rather than throwing or rendering undefined.
**Invariant:** default-first translation: the generic string is assigned BEFORE the switch, so any new server code added without a matching case degrades to "An unexpected error occurred" — never a blank toast, never a crash. The cast `as AppErrorCode` is a lie by design (the wire carries plain strings from `handleServerError`); correctness lives entirely in the switch/default pairing, so porters must keep the two code sets in lockstep manually.
**Probe:** deterministic grep anchors (executed): `grep -c 'case "' apps/web/src/lib/safe-action/client.ts` → 8 (one per projected code); `grep -n 'router.refresh()' apps/web/src/lib/safe-action/client.ts` → line 14. No dedicated upstream test for the hook.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "rallly", query: "useSafeAction serverError toast", limit: 5 });
```

## Verdict
Adopt the wrapper pattern (refresh-on-success + default-first code switch) verbatim; adapt the i18n call shape; omit nothing else — the hook is 72 lines and self-contained. Consumer example: `poll-mute-owner-scoped-toggle`.
