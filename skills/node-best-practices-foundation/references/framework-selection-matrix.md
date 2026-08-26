<!-- capsule-v2 -->
# Framework selection consequences matrix — which team/app signals pick express vs Nest vs Fastify vs Koa?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** What decision factors does upstream weight when choosing the core framework, and which matchings does it prescribe?

## Popularity-weighted pros/cons per framework + four explicit "prefer X when" rules keyed to team skill & app shape
**Path/Symbol:** `sections/projectstructre/choose-framework.md` (:5 popularity-supreme premise), (:7-33 express/Nest/Fastify/Koa pros-cons), (:35-39 choosing guide).
**Signature:** Prefer express ⟸ experienced architect onboard AND fine-grained control needed (Koa = modern-API alternative, smaller ecosystem). Prefer Fastify ⟸ reasonably-sized components/microservices + solid JS/Node team + staying close to Node narratives. Prefer Nest ⟸ OOP style desired OR Java/Spring/Angular-experienced team OR large monolith-to-autonomous-components OR JS-skill-lacking team OR minimal decision overhead / time-to-first-delivery critical.
**Data Shape:** tradeoff axes = ecosystem size, batteries included, abstraction level, learning curve, opinionation.

### Decisive source
```text
# choose-framework.md :5 — the stated weighting
choosing the core framework determines strategic factors like the development
style and how likely the team is to hit a wall. We believe that framework
popularity is a supreme consideration...
# :37 — one prescribed matching verbatim
Prefer Fastify when - The app consists of reasonably-sized
components/Microservices (i.e., not a huge monolith); for teams who have
solid JavaScript & Node.js knowledge; when sticking to Node.js narratives
and spirit is desirable
```

**Flow:** assess team skills + app decomposition FIRST → map to the four prescriptions → accept each framework's documented cons knowingly (express: no native async-await era mechanics, thin coverage needing many decisions; Nest: abstraction clouding Node conventions + steeper curve; Koa/Fastify: smaller ecosystems).
**Invariant:** the choice is STRATEGIC (development style + wall-hitting likelihood), not a syntax preference — hence popularity (ecosystem/help availability) outranks elegance. Express's "merely a web server that invokes the app function per URL" means choosing it = choosing to assemble the rest yourself.
**Probe:** no runner upstream. Deterministic probe: `grep -c 'Prefer Nest.js when' sections/projectstructre/choose-framework.md` >= 1 && `grep -c 'supreme consideration' sections/projectstructre/choose-framework.md` >= 1.
**Retrieve:** `await mcp.codebase_memory.search_code({ project: "nodebestpractices", pattern: "choose-framework", limit: 5 });`

## Verdict
Adopt the signal→framework mappings and the popularity-weighting rationale for greenfield choices. Adapt weights to your org's hiring reality. Omit star/download counts (era-specific); revisit against current maintenance status before deciding.
