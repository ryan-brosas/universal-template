import { projectIdentity } from './identity.mjs';
import { join } from 'node:path';
import { projectScoped } from './memory.mjs';

// Automatic trigger policy. Component-side queueing only: actors receive one
// bounded activation per event class; their replies cannot spawn more work.
export const AUTO_ROLES = {
  scout: { stage: 'input', delivery: 'mailbox', triggerTurn: false, name: id => 'auto-scout-' + id },
  supervisor: { stage: 'input', delivery: 'mailbox', triggerTurn: false, name: id => 'auto-supervisor-' + id },
  verifier: { stage: 'settled', delivery: 'mailbox', triggerTurn: false, name: id => 'auto-verifier-' + id },
  advisor: { stage: 'settled', delivery: 'mailbox', triggerTurn: false, name: id => 'auto-advisor-' + id },
  reflector: { stage: 'compact', delivery: 'mailbox', triggerTurn: false, name: id => 'auto-reflector-' + id },
  foundation: { stage: 'compact', delivery: 'followUp', triggerTurn: false, name: id => 'auto-foundation-' + id },
};

const READ_ONLY_TOOLS = ['read', 'grep', 'find', 'ls'];

export const STAGES = { input: ['scout', 'supervisor'], settled: ['verifier', 'advisor'], compact: ['reflector', 'foundation'] };

export async function buildTriggers(context, config, extensions, existingRows) {
  const ctx = context.invocation.extensionContext;
  const identity = await projectIdentity(ctx.cwd);
  const sessionId = ctx.sessionManager.getSessionId();
  const memory = projectScoped(identity, extensions);
  const broker = { identity, memory, sessionId };
  const desired = [];
  for (const [role, policy] of Object.entries(AUTO_ROLES)) {
    const name = policy.name(identity.id) + '-readonly-v1';
    const matches = existingRows.filter(row => row.name === name);
    if (matches.length > 1) throw Error('Ambiguous auto actor ' + name);
    const prior = matches[0];
    if (prior) {
      if (prior.extensions !== false || !Array.isArray(prior.tools) ||
          prior.tools.length !== READ_ONLY_TOOLS.length ||
          !READ_ONLY_TOOLS.every(tool => prior.tools.includes(tool))) {
        throw Error('Unsafe auto actor ' + name + ': extensions must be disabled and tools read-only');
      }
      desired.push({ role, policy, actor: prior, reused: true });
      continue;
    }
    desired.push({ role, policy, reused: false, actor: await context.call('agents.create', {
      name,
      runner: 'pi',
      residency: 'durable',
      extensions: false,
      transport: 'process',
      ...(config.model ? { model: config.model } : {}),
      responseMode: 'directive',
      delivery: policy.delivery,
      triggerTurn: policy.triggerTurn,
      coalesce: true,
      events: [],
      tools: [...READ_ONLY_TOOLS],
      instructions: 'Read ' + JSON.stringify(join(config.roleDir, role + '.md')) + ' on each activation and follow that role. Return only a Fabric directive.',
    }) });
  }
  return { identity, broker, desired };
}

export function shouldTrigger(stage, context) {
  if (context.child() || !context.trusted) return false;
  return STAGES[stage]?.length > 0;
}

export function scopeKey(stage, session, checkpoint) {
  return stage + '/' + session + '/' + (checkpoint ?? 'live');
}
