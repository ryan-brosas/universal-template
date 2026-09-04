<!-- capsule-v2 -->
# Postpone reason tagged union — How is "why was this action postponed" typed so both bare strings and structured reasons validate?

**Source:** Linked Helper v2.130.5 ingest (proprietary — citations-only), pin `?@?`; Codebase Memory `lh-basis` @ 2026-08-23T00:11:49Z. **Question:** how does one slot hold six dataless reasons, two limit-backed reasons, and a serialized error without becoming an untyped string?

## Four validators over one `type`-tagged union
**Path/Symbol:** `core/public-methods/models/actions/PostponeReason/guards.js` — `isTPostponeReasonWithoutData` (11–22), `isIPostponeLHLimitReason` (23–30), `isIPostponeLinkedInLimitReason` (31–36), `isIPostponeErrorReason` (37–51).
**Signature:** all `(data): boolean`; consumed from `Action.postponeReason` (see action-lifecycle-guards).
**Data Shape:** union of `{type:'Manually'|'IterationLimitReached'|'Waiter'|'TooManyErrors'|'TooManyFails'|'InsufficientLHEmailFinderCredits'}` | bare string of the same six | `{type:'LHLimit', limitType: ILimitType|number|string}` | `{type:'LinkedInLimit', limitType:string}` | `{type:'Error', error:{isException,whoToBlame,isRetryable,code,message,name,stack,'[dump]'}}`.

### Decisive source
```js
function isTPostponeReasonWithoutData(data) {
    const supportedReasons = ['Manually','IterationLimitReached','Waiter','TooManyErrors','TooManyFails','InsufficientLHEmailFinderCredits'];
    const currentReason = ((0, objects_1.isObject)(data) && data?.type ? data.type : data);   // dual acceptance
    return supportedReasons.includes(currentReason);
}
function isIPostponeLHLimitReason(data) {
    const arg = data;
    return (arg?.type === 'LHLimit' && Boolean(arg?.limitType) &&
        ((0, guards_1.isILimitType)(arg.limitType) || ['string', 'number'].includes(typeof arg.limitType)));  // polymorphic ref
}
function isIPostponeLinkedInLimitReason(data) {
    return data?.type === 'LinkedInLimit' && typeof data?.limitType === 'string';            // LinkedIn's own name, string-only
}
// isIPostponeErrorReason: type==='Error' ∧ error envelope with
//   whoToBlame ∈ ['LinkedIn','Proxy','LH','User'], isException/isRetryable:boolean,
//   code:null|number, message/name:string, stack/'[dump]':string|undefined
```

**Flow:** read the tag (`data.type`, falling back to the value itself) -> dispatch to the matching validator -> each arm pins its payload shape; the Error arm validates a SERIALIZED error envelope (booleans + blame taxonomy + optional `[dump]` text), never an `instanceof Error`.
**Invariant:** limit references are polymorphic by design — a full ILimitType object, its numeric id, or its code string are all legal for LHLimit, while LinkedInLimit accepts only LinkedIn's own string name; truthiness of `limitType` is required before type checks (empty string fails). The four-way blame taxonomy (LinkedIn | Proxy | LH | User) is the retry/attribution vocabulary.
**Probe:** deterministic node-require:
```bash
node -e "const g=require('/mnt/hdd/utopia/inspo/lh-basis/core/public-methods/models/actions/PostponeReason/guards.js');console.log(g.isTPostponeReasonWithoutData('Waiter'),g.isTPostponeReasonWithoutData({type:'TooManyErrors'}),g.isIPostponeLHLimitReason({type:'LHLimit',limitType:'inviteOverWeeklyLimit'}),g.isIPostponeLHLimitReason({type:'LHLimit',limitType:0}),g.isIPostponeLinkedInLimitReason({type:'LinkedInLimit',limitType:'connections'}),g.isIPostponeErrorReason({type:'Error',error:{isException:true,whoToBlame:'Proxy',isRetryable:true,code:null,message:'m',name:'E',stack:undefined,'[dump]':undefined}}),g.isIPostponeErrorReason({type:'Error',error:{isException:true,whoToBlame:'Aliens',isRetryable:false,code:1,message:'m',name:'E'}}))"
```
→ expect `true true true false true true false` (limitType 0 rejected by the truthiness gate; unknown whoToBlame rejected).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "lh-basis", query: "postpone reason guard", file_pattern: "*PostponeReason*", limit: 10 });
```
Observed pass 3: returns all four validators (11–51).

## Verdict
Adopt: tag-with-fallback validation, polymorphic id-or-object-or-code references for internal limits, and a serialized-error envelope with an explicit blame taxonomy instead of instanceof chains. Adapt reason names and blame categories to your host. Omit LinkedIn-specific limit names. Caveat: no upstream tests in this ingest — deterministic probe only.
