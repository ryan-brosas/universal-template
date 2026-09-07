import { digest } from './identity.mjs';

// Calls through this broker are project-pinned. This is not a sandbox for
// extension-enabled actors: direct actor tool calls bypass this wrapper.
export const failure = reason => ({ degraded: true, reason, rows: [], proposals: [] });

// Captured extension tools carry JSON in text/content; details may contain only
// bank metadata. Preserve direct responses for injected clients and unit tests.
function responsePayload(result, field) {
  if (!result || result.isError) throw new Error('Hindsight returned an error');
  if (result.details?.[field] !== undefined) return result.details;
  if (result[field] !== undefined) return result;
  const text = result.text ?? result.content?.filter(c => c.type === 'text').map(c => c.text).join('\n');
  if (typeof text !== 'string') throw new Error('missing Hindsight payload');
  const payload = JSON.parse(text);
  if (!payload || typeof payload !== 'object' || payload.isError) throw new Error('invalid Hindsight payload');
  return payload;
}

export function projectScoped(identity, extensions) {
  if (!extensions) return failure('Fabric extensions unavailable');
  return {
    projectId: identity.projectId,
    bankId: identity.bankId,
    roleTag: role => 'crew-role:' + role,
    async recall(role, query, { budget = 'low', maxTokens = 800 } = {}) {
      try {
        const result = await extensions.hindsight_recall({
          query,
          bank: identity.bankId,
          tags: ['crew-role:' + role],
          tagsMatch: 'all_strict',
          budget,
          maxTokens,
        });
        const payload = responsePayload(result, 'results');
        if (!Array.isArray(payload.results)) throw new Error('invalid recall results');
        return { degraded: false, rows: payload.results };
      } catch (error) {
        return failure('recall unavailable: ' + error.message);
      }
    },
    async propose(role, { content, context, session, checkpoint, kind, documentId }) {
      if (!content?.trim()) return failure('empty proposal');
      try {
        const result = await extensions.hindsight_retain({
          content: content.trim(),
          ...(documentId ? { documentId } : {}),
          context: '[' + identity.projectId + '] crew ' + role + ' ' + kind + ': ' + context,
          bank: identity.bankId,
          tags: ['crew-role:' + role, 'crew-kind:' + kind, 'crew-session:' + (session ?? 'unknown'), 'crew-checkpoint:' + (checkpoint ?? 'unknown')],
          metadata: { crewProject: identity.projectId, crewRole: role, crewKind: kind },
        });
        const payload = responsePayload(result, 'documentId');
        if (typeof payload.documentId !== 'string' || !payload.documentId.trim()) throw new Error('missing retain receipt');
        return { degraded: false, documentId: payload.documentId, ...((payload.enqueued === true || payload.queued === true) ? { queued: true } : {}) };
      } catch (error) {
        return failure('retain unavailable: ' + error.message);
      }
    },
  };
}

export { digest };
