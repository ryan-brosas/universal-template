<!-- capsule-v2 -->
# Platform and verify — is the Node project npm-safe and cross-platform ready?

**Source:** microsoft/nodejs-guidelines (getting-started, windows-environment, building-for-cross-platform, deployment). **Question:** Are dependencies, paths, native modules, and deployment patterns safe on Microsoft and cross-platform targets?

## npm packaging seam
**Path/Symbol:** Node app repo root `package.json`, `.gitignore`, server entry.
**Signature:** pinned deps; node_modules ignored; PORT from env; npm scripts over global tools.
**Data Shape:** `npm install` reproducible; short Windows paths when relevant.

### Decisive pattern
```json
{
  "dependencies": {
    "express": "^4.18.0"
  },
  "scripts": {
    "start": "node app.js"
  }
}
```

```js
const port = process.env.PORT || 3000;
server.listen(port);
```

**Flow:** declare runtime deps in **package.json** (`npm install pkg --save`; dev tools `--save-dev`) → **do not commit** `node_modules` — document `npm install` restore → avoid `"*"` wild versions for production → prefer **local** deps + npm scripts over **global `-g`** when versions differ per project → use **npm-shrinkwrap**/lockfile when teams require exact installs → server apps: **`process.env.PORT || fallback`** → Windows dev: use **short base paths** (e.g. `C:\src`) to mitigate **MAX_PATH** → run **npm dedupe** / flat npm 3+ trees when path length bites → identify **native addons** (`node-gyp`, `nan`, `node-pre-gyp`) and document **windows-build-tools** or VS build prerequisites → public modules should be **cross-platform** (Windows + Linux + macOS) unless explicitly private → deployment: consider process managers (PM2/forever) for restart — not nodemon in production.
**Invariant:** committed node_modules, unbounded deps, or Windows-only public package without platform guard fails platform review.
**Probe:** git status node_modules; package.json dependency pins; native module dependency grep; README documents Windows build if native.

## Verify seam
**Flow:** ESLint with felixge-aligned or modern JS rules + EditorConfig → `npm test` / `npm start` on changed module → optional: install native test packages (bson, sqlite3) on Windows CI when addon present → cross-platform smoke on target OS.
**Probe:**
```bash
npm install
npm test
node -e "require('./app')"
```

## Verdict
package.json + gitignored node_modules, env PORT, Windows path awareness, cross-platform native discipline. Learning note: `node-style-learning-note.md`.
