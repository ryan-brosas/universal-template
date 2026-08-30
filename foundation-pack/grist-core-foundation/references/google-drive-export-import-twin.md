<!-- capsule-v2 -->
# Google Drive export/import twin — how does grist push a doc TO Drive and pull one back, and why do the two directions authenticate so differently?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** What are the auth models, mime-type conversions, and error-translation contracts of the Drive integration plane?

## Outbound: user oauth token + xlsx→gspreadsheet conversion; inbound: server API key + gspreadsheet→xlsx export
**Path/Symbol:** outbound `app/server/lib/GoogleExport.ts` — `exportToDrive(activeDoc, req, res)` (:16–63), `sendFileToDrive` (:66–91); inbound `app/server/lib/GoogleImport.ts` — `downloadFromGDrive(url, code?)` (:14–43), `initDriveApi` (:45–57), error bridge `asFetchResponse` (:59–87), `fileIdFromUrl` (:93–97); routes: DocApi.ts :1293 (`/send-to-drive`, middleware `canView, decodeGoogleToken, withDoc`) and the import-side caller in ActiveDoc/DocManager import path.
**Signature:** `files.create({requestBody:{name, mimeType:"application/vnd.google-apps.spreadsheet"}, oauth_token, media:{mimeType:"application/vnd.ms-excel", body: stream}, fields:"webViewLink"})` vs `files.get/export({key, fileId, alt:"media", mimeType:XLSX_MIMETYPE})`.
**Data Shape:** outbound streams XLSX bytes through a PassThrough consumed by Google's SDK while `streamXLSX` writes it (Promise.all pairing); inbound returns a node-fetch `Response` whose headers carry a synthesized `content-disposition`.

### Decisive source
```ts
// GoogleExport.ts:40-43 — export and upload run CONCURRENTLY over one stream
const [, url] = await Promise.all([
      streamXLSX(activeDoc, req, stream, { tableId: "" }),
      sendFileToDrive(name, stream, access_token),
]);
// GoogleExport.ts:54-61 — unwrap Google's error envelope, else rethrow untouched
} catch (err) {
    if (err.errors?.length) {
      throw new Error(err.errors[0].message);
    } else {
      throw err;
    }
}
// GoogleImport.ts:28-36 — spreadsheets must be EXPORTED as xlsx; other files stream raw
if (fileRes.data.mimeType === SPREADSHEETS_MIMETYPE) {
      let filename = fileRes.data.name;
      if (filename && !filename.includes(".")) {
        filename = `${filename}.xlsx`;
      }
      return await asFetchResponse(googleDrive.files.export(
        { key, fileId, alt: "media", mimeType: XLSX_MIMETYPE },
        { responseType: "stream" },
      ), filename);
}
// GoogleImport.ts:71-86 — Gaxios errors translated INTO fetch semantics
} catch (err) {
    const error: GaxiosError<Readable> = err;
    if (!error.response) {
      // Fetch throws exception on network error.
      throw new FetchError(error.message, "system", error);
    } else {
      // Fetch returns failure response on http error
      const resInit = ...;
      return new FetchResponse(error.response.data, resInit);   // HTTP error becomes a RESPONSE, not a throw
    }
}
```

**Invariant:** (1) **Auth asymmetry is directional**: pushing to a user's Drive needs THEIR oauth token (middleware `decodeGoogleToken` put it on the query; missing → hard throw :22–25), while pulling PUBLIC files needs only a SERVER-WIDE `GOOGLE_API_KEY` (throw if unset :16–18); an optional oauth `code` upgrades inbound pulls to authenticated drives via `initDriveApi(code)`. (2) Conversion is asymmetric too: outbound asks Drive to convert xlsx→native spreadsheet by declaring the TARGET mimeType in `requestBody` while sending `application/vnd.ms-excel`; inbound asks Drive to EXPORT native sheets as `XLSX_MIMETYPE` and appends `.xlsx` when the name lacks a dot (idempotence guard). (3) Inbound HTTP-level failures become normal fetch Responses (status preserved) so downstream upload code handles them like any URL download; only NETWORK failures throw — this matches `upload-url-fetch-ladder` expectations. (4) Audit event `document.send_to_google_drive` fires on success with doc id (GoogleExport.ts:44–51). (5) URL parsing accepts only `https://(docs|drive).google.com/(spreadsheets|file)/d/<id>` (case-insensitive, :95).

**Flow:** send-to-drive route → decodeGoogleToken → withDoc(exportToDrive) → concurrent streamXLSX+upload → `{url}` json reply. Import side: `isDriveUrl` gate on pasted URLs → `downloadFromGDrive` → Response flows into the standard upload/import funnel.

**Probe:** deterministic greps:
```bash
cd /mnt/hdd/utopia/inspo/grist-core
grep -n 'oauth_token' app/server/lib/GoogleExport.ts | cut -d: -f1   # 66 82
grep -nF 'process.env.GOOGLE_API_KEY' app/server/lib/GoogleImport.ts # 16
grep -nF 'drive({ version: "v3" })' app/server/lib/GoogleImport.ts   # 56 keyless public arm
grep -n 'err.errors?.length' app/server/lib/GoogleExport.ts          # 57
grep -n 'throw new FetchError(error.message' app/server/lib/GoogleImport.ts  # 76
grep -c 'fileIdFromUrl' app/server/lib/GoogleImport.ts               # 3
```
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "download google drive import url fetch response stream", limit: 5 });
// → app.server.lib.GoogleImport.asFetchResponse Function 59-87 (+ Importer._fetchFromDrive client twin)
```

## Verdict
Adopt the directional-auth split (user-token for user-space writes, server-key for public reads) for any third-party storage bridge. Adopt the gaxios→fetch error-shape normalization whenever two HTTP clients meet at one boundary — downstream code should see ONE error philosophy. The concurrent export/upload Promise.all is adopt-worthy but note its coupling: neither side can retry independently.
