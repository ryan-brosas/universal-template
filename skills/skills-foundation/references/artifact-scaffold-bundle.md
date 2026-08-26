<!-- capsule-v2 -->
# Artifact Scaffold-and-Bundle — how does a two-shell-script pipeline take a repo from empty directory to single-file HTML artifact?

**Source:** anthropics/skills (Apache-2.0) `main@3b3fad96`; Codebase Memory `skills`. **Question:** What environment adaptation does init-artifact.sh perform, and what is the exact bundle path to one self-contained HTML file?

## Version-gated scaffold → parcel build → full inline
**Path/Symbol:** `skills/web-artifacts-builder/scripts/init-artifact.sh` (322L, read whole) + `bundle-artifact.sh` (53L, read whole).
**Signature:** CLI scripts; init takes `$1` = project name, must run beside `shadcn-components.tarball` (`$SCRIPT_DIR/shadcn-components.tar.gz`); bundle runs from project root requiring `package.json` + `index.html`.
**Data Shape:** Node-version gates: `<18` hard-fail; `18 ≤ v < 20` pins `vite@5.4.11`, else latest. OS gate: darwin gets `SED_INPLACE="sed -i ''"`, linux `"sed -i"`. JSON-with-comments handling in tsconfig.app.json done via `node -e`: strip `//` lines → strip `/*…*/` → remove trailing commas before `}`/`]` → JSON.parse.

### Decisive source
```bash
if [ "$NODE_VERSION" -ge 20 ]; then
  VITE_VERSION="latest"
else
  VITE_VERSION="5.4.11"     # Node 18 compatibility pin
fi
...
node -e "
const config = JSON.parse(jsonContent.replace(/\/\*[\s\S]*?\*\//g, '').replace(/,(\s*[}\]])/g, '\$1'));
config.compilerOptions = config.compilerOptions || {};
config.compilerOptions.paths = { '@/*': ['./src/*'] };
..."
```
```bash
# bundle-artifact.sh — the whole pipeline:
cat > .parcelrc << 'EOF'
{ "extends": "@parcel/config-default",
  "resolvers": ["parcel-resolver-tspaths", "..."] }
EOF
rm -rf dist bundle.html
pnpm exec parcel build index.html --dist-dir dist --no-source-maps
pnpm exec html-inline dist/index.html > bundle.html
```

**Flow (init):** version/OS detection → pnpm bootstrap if missing → create-vite react-ts scaffold → sed-clean template favicon/title → base install → Tailwind 3.4.1 + shadcn theme tokens written as whole files → `@/*` path alias into BOTH tsconfigs + vite alias → all Radix primitives + utility deps in one shot → tarball-extract 40+ prebuilt components into src/ → components.json manifest.
**Flow (bundle):** install parcel + tspaths resolver + html-inline → .parcelrc extends default with tspaths resolver FIRST (the `...` passthrough keeps default resolution after) → clean dist → build with no source maps → html-inline folds JS/CSS into ONE file sized by du.
**Invariant:** The scaffold is OPINION-PINNED so the LLM doesn't re-derive choices: exact Tailwind token block, fixed alias set, vendored component tarball instead of interactive shadcn init. The bundle's product definition is "single HTML file that survives as a chat artifact" — hence no-source-maps and total inlining; tspaths-resolver exists because Parcel ignores TS path aliases natively. Idempotence: .parcelrc only written when absent.
**Probe:** No upstream tests. Deterministic probes (anchors re-derived & executed 2026-08-24): `grep -c 'VITE_VERSION="5.4.11"' skills/web-artifacts-builder/scripts/init-artifact.sh` = 1; `grep -c 'html-inline' skills/web-artifacts-builder/scripts/bundle-artifact.sh` = 2; `grep -c 'parcel-resolver-tspaths' skills/web-artifacts-builder/scripts/bundle-artifact.sh` = 2.
**Coverage caveat:** network-dependent scaffolding; pinned versions drift upstream over time.

## Get live surrounding code
**Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "skills", "pattern": "parcel-resolver-tspaths", "limit": 10}'
# resolves `skills/web-artifacts-builder/scripts/bundle-artifact.sh` line-exact (:21;:29) + SKILL.md (verified 2026-08-24)
```

## Verdict
Adopt for any agent-driven project scaffolding: detect-then-pin environment matrices, write whole opinionated config files rather than patching templates, vendor component packs for determinism, and finish with a single-file artifact contract. Adapt package manager/pins to your stack; keep the resolver-order comment (`["tspaths", "..."]`) intact or aliases break.
