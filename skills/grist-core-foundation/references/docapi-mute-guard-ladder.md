<!-- capsule-v2 -->
# DocApi mute guard ladder — how does an API handler fail fast when the document is torn down mid-request?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How do you convert "the ActiveDoc was muted/shut down while we were processing" into one clean HTTP error, even when the real failure surfaces as some unrelated exception?

## Post-hoc mute check replaces every mid-flight error with one 503
**Path/Symbol:** `app/server/lib/DocApi.ts:DocWorkerApi._requireActiveDoc` (:1843–1855), `_checkForMute` (:1830–1834); mutators `activeDoc.setMuted()`/`shutdown()` at `/assign` (:1007–1015).
**Signature:** `_requireActiveDoc(callback: WithDocHandler): RequestHandler`; `WithDocHandler = (activeDoc: ActiveDoc, req: RequestWithLogin, res: Response) => Promise<void>`.
**Data Shape:** Mute is a boolean flag on ActiveDoc (`activeDoc.muted`). The wrapper resolves the ActiveDoc promise itself (`this._getActiveDoc(req)`) before invoking the callback; every `withDoc(...)` route body therefore receives `(activeDoc, req, res)` instead of express's `(req, res)`.

### Decisive source
```ts
private _requireActiveDoc(callback: WithDocHandler): RequestHandler {
    return async (req, res) => {
      let activeDoc: ActiveDoc | undefined;
      try {
        activeDoc = await this._getActiveDoc(req as RequestWithLogin);
        await callback(activeDoc, req as RequestWithLogin, res);
        if (!res.headersSent) { this._checkForMute(activeDoc); }   // success path check
      } catch (err) {
        this._checkForMute(activeDoc);                             // replaces ANY error...
        throw err;                                                 // ...only when not muted
      }
    };
}
// _checkForMute: if (activeDoc?.muted) throw new ApiError("Document in flux - try again later", 503);
```
**Flow:** fetch ActiveDoc → run handler → on success, IF headers not yet sent, re-check mute (a doc that died after the response began can't be reported anyway) → on any thrown error, FIRST check mute: if muted, the 503 "in flux" error *replaces* whatever confusing error the shutdown caused; otherwise the original error propagates to the jsonErrorHandler.
**Invariant:** the mute check must run AFTER the handler and in BOTH paths (success-without-headers and catch), because shutdown during processing manifests as arbitrary downstream errors, not one typed exception. Never report mute once headers are sent — the client already got a response. `/assign` deliberately mutes then shuts down (`interruptAllClients(); setMuted(); shutdown()`) so concurrent in-flight requests drain as 503s rather than hangs.
**Probe:** `test/server/lib/docapi/DocApiDocuments.ts` (`POST /docs/{did}/replace` / `/assign` suite, :5–77 incl. "allows assignments") exercises the assign→mute→shutdown path; no dedicated 503 unit exists upstream — coverage caveat: the replacement semantics of `_checkForMute` are source-pinned only.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "_requireActiveDoc _checkForMute muted ApiError 503", limit: 8,
  fields: ["signature", "name", "file"] });
```
**Verdict:** Adopt the wrap-and-recheck pattern for any long-running handler over an evictable resource (doc, session, cache entry): one sentinel flag + post-hoc check beats threading a cancellation token through every callee. Adapt the status code/message to your surface. Omit the headersSent nuance only if your responses are never streamed.
