// Discord web: read the guild rail, a guild's channel list, a forum's posts and a channel tail.
//
// Derived from live work on 2026-09-25/26. The selectors, the lazy-load behaviour, the folder rows
// and the serialisation rule are recorded in notes/reading-surfaces.md; the reply mechanics live in
// tools/reply_to_message.mjs.
//
// ctx is { session, sessionId?, cdp?, sleep? }: pass the harness session plus, when the caller
// already attached to a tab, its sessionId. `cdp` overrides the default session._call routing.

const DEFAULTS = { settleMs: 2600, retryMs: 1800, retries: 5, limit: 8, messageSettleMs: 3200 };

export function maskMentions(text) {
  return String(text ?? '').replace(/@[\w.\-]{2,32}/g, '[mention]');
}

function prepare(ctx) {
  const session = ctx?.session;
  if (!session) throw new Error('read_surfaces needs an active CDP session in ctx.session');
  const call = ctx.cdp || ((sid, method, params = {}) =>
    session._call(method, params, sid ? { sessionId: sid } : {}));
  const evaluate = async (expression) => {
    const r = await call(ctx.sessionId, 'Runtime.evaluate', { expression, returnByValue: true });
    const value = r?.result?.value;
    return value ? JSON.parse(value) : null;
  };
  const navigate = (url) => call(ctx.sessionId, 'Page.navigate', { url });
  const sleep = ctx.sleep || ((ms) => new Promise((r) => setTimeout(r, ms)));
  return { evaluate, navigate, sleep };
}

// A read can be empty because Discord still has to render, and re-navigating on every attempt resets
// that render. Navigate once, poll for rows, then allow exactly one re-navigation as a fallback.
async function readWithPolling(ctx, args) {
  const { url, expression, settleMs, retryMs, polls, doubleSettle = true } = args;
  const { evaluate, navigate, sleep } = prepare(ctx);
  let data = [];
  let attempts = 0;
  await navigate(url);
  await sleep(settleMs);
  for (let i = 0; i < polls; i++) {
    attempts++;
    data = (await evaluate(expression)) || [];
    if (data.length) return { data, attempts };
    await sleep(retryMs);
  }
  if (!doubleSettle) return { data, attempts };
  await navigate(url);
  await sleep(settleMs * 2);
  attempts++;
  data = (await evaluate(expression)) || [];
  return { data, attempts };
}

// Rail rows: servers are div.wrapper__... with aria-level 1, or 2 when they sit inside an open folder.
// Folder rows are div.folderButton__... whose hidden span concatenates their members and then the word
// "folder". aria-level 1 aria-setsize is the number of top-level rows (folders included), not the
// number of servers, so counting `guildsnav___` items overstates membership.
const GUILDS_EXPR = `(()=>{
  const strip=t=>String(t||'').replace(/,\\s*[\\d,]+\\s*unread mentions?\\s*$/i,'').replace(/,\\s*folder\\s*$/i,'').replace(/\\s+/g,' ').trim();
  const items=[...document.querySelectorAll('[data-list-item-id^="guildsnav___"]')];
  const servers=[],folders=[];
  for(const el of items){
    const id=(el.getAttribute('data-list-item-id')||'').slice('guildsnav___'.length);
    const span=el.querySelector('span[class*=hiddenVisually]')||el.querySelector('span');
    const raw=strip(span?span.textContent:(el.innerText||''));
    const text=(el.innerText||'').replace(/\\s+/g,' ').trim();
    const isFolder=/folderButton/.test(String(el.className))||/,\\s*folder\\b/i.test(String(span?span.textContent:''));
    const name=raw.replace(/^(unread messages|mention|new messages|unread)[,\\s]+/i,'').trim();
    const unread=/(^|[,\\s])(unread messages|unread mentions?|mention)\\b/i.test(text);
    const level=Number(el.getAttribute('aria-level'))||null;
    const pos=Number(el.getAttribute('aria-posinset'))||null;
    const size=Number(el.getAttribute('aria-setsize'))||null;
    if(isFolder){
      const list=name.split(',').map(s=>s.trim()).filter(Boolean);
      const truncated=list.slice(-1)[0]==='...';
      folders.push({id,members:truncated?list.slice(0,-1):list,membersTruncated:truncated,expanded:el.getAttribute('aria-expanded')==='true',level,pos,size,unread});
    } else if(id && id!=='home'){
      servers.push({id,name,unread,level,pos,size});
    }
  }
  return JSON.stringify({servers,folders});
})()`;

// Real channels are <a href="/channels/<guild>/<cid>">; categories and the events button are divs
// without an href. aria-label is authoritative: "providers (text channel)", "server (category)".
const CHANNELS_EXPR = `(()=>{
  const items=[...document.querySelectorAll('[data-list-item-id^="channels___"]')];
  return JSON.stringify(items.map(el=>{
    const label=el.getAttribute('aria-label')||'';
    const a=el.matches('a[href*="/channels/"]')?el:el.querySelector('a[href*="/channels/"]');
    const m=/\\/channels\\/(\\d+)\\/(\\d+)/.exec(a?a.getAttribute('href')||'':'');
    const kind=(/\\(([^)]*)\\)\\s*$/.exec(label)||[])[1]||'';
    return {cid:m?m[2]:null,gid:m?m[1]:null,name:label.replace(/\\s*\\([^)]*\\)\\s*$/,'').trim(),kind,label};
  }));
})()`;

// Post rows carry both halves of what you need in the id and the aria-label:
// forum-channel-list-<forumChannelId>___<threadId> and "Post <title>, <n> message(s)".
const FORUM_EXPR = `(()=>{
  const items=[...document.querySelectorAll('[data-list-item-id^="forum-channel-list"]')];
  const out=[];
  for(const el of items){
    const tid=((el.getAttribute('data-list-item-id')||'').split('___')[1]||'');
    if(!/^\\d{15,}$/.test(tid))continue;
    const label=el.getAttribute('aria-label')||'';
    const m=/^Post (.+?)(?:,\\s*(\\d+)\\s+messages?)?$/.exec(label);
    out.push({tid,title:m?m[1]:label.replace(/^Post /,''),messageCount:m&&m[2]!==undefined?Number(m[2]):null});
  }
  return JSON.stringify(out);
})()`;

// Discord virtualises the list, so only rendered rows exist; read at the channel end and take the
// row's own message-content element, never the first one, which can be the quoted preview.
const messagesExpr = (limit) => `(()=>{
  const rows=[...document.querySelectorAll('li[id^=chat-messages-]')].slice(-${limit});
  return JSON.stringify(rows.map(li=>{
    const id=li.id.split('-').pop();
    const own=li.querySelector('[id="message-content-'+id+'"]');
    const time=li.querySelector('time');
    const author=li.querySelector('[id^=message-username-]');
    const quoted=li.querySelector('[class*=repliedMessage] [id^=message-content-]');
    return {id,time:time?time.getAttribute('datetime'):null,author:author?author.textContent.trim():null,text:own?own.textContent.trim().replace(/\\s+/g,' '):null,quoted:quoted?quoted.textContent.trim().replace(/\\s+/g,' ').slice(0,200):null};
  }).filter(m=>m.text));
})()`;

export async function listGuildRail(ctx) {
  const { evaluate } = prepare(ctx);
  const rail = (await evaluate(GUILDS_EXPR)) || { servers: [], folders: [] };
  const topLevel = rail.servers.filter((s) => s.level === 1);
  return {
    servers: rail.servers,
    folders: rail.folders,
    total: topLevel.find((s) => s.size)?.size ?? topLevel.length,
  };
}

export async function listChannels(ctx, args = {}) {
  const { guildId, previous = [] } = args;
  if (!guildId) throw new Error('listChannels needs a guildId');
  const settleMs = args.settleMs ?? DEFAULTS.settleMs;
  const retryMs = args.retryMs ?? DEFAULTS.retryMs;
  const retries = args.retries ?? DEFAULTS.retries;
  const { evaluate, navigate, sleep } = prepare(ctx);
  const seen = new Set(previous);
  const url = 'https://discord.com/channels/' + guildId;
  let channels = [];
  let attempts = 0;
  const stale = () => channels.length > 0 && seen.size > 0 && channels.every((c) => !c.cid || seen.has(c.cid));
  await navigate(url);
  await sleep(settleMs);
  for (let i = 0; i < retries; i++) {
    attempts++;
    channels = (await evaluate(CHANNELS_EXPR)) || [];
    if (channels.length && !stale()) return { guildId, channels, attempts, stale: false };
    await sleep(retryMs);
  }
  // One re-navigation, for a guild whose sidebar never left the previous server.
  await navigate(url);
  await sleep(settleMs * 2);
  attempts++;
  channels = (await evaluate(CHANNELS_EXPR)) || [];
  return { guildId, channels, attempts, stale: stale() };
}

export async function listForumPosts(ctx, args = {}) {
  const { guildId, forumChannelId } = args;
  if (!guildId || !forumChannelId) throw new Error('listForumPosts needs guildId and forumChannelId');
  const { data, attempts } = await readWithPolling(ctx, {
    url: 'https://discord.com/channels/' + guildId + '/' + forumChannelId,
    expression: FORUM_EXPR,
    settleMs: args.settleMs ?? DEFAULTS.messageSettleMs,
    retryMs: args.retryMs ?? DEFAULTS.retryMs,
    polls: args.retries ?? DEFAULTS.retries,
  });
  return { forumChannelId, posts: data, attempts };
}

export async function readChannelEnd(ctx, args = {}) {
  const { channelUrl, mask = false } = args;
  if (!channelUrl) throw new Error('readChannelEnd needs a channelUrl');
  const limit = args.limit ?? DEFAULTS.limit;
  const { data, attempts } = await readWithPolling(ctx, {
    url: channelUrl,
    expression: messagesExpr(limit),
    settleMs: args.settleMs ?? DEFAULTS.messageSettleMs,
    retryMs: args.retryMs ?? DEFAULTS.retryMs,
    polls: args.retries ?? 3,
  });
  // An empty result is unknown, not an idle channel: the caller decides after seeing `attempts`.
  const messages = mask
    ? data.map((m) => ({ ...m, text: maskMentions(m.text), quoted: maskMentions(m.quoted) }))
    : data;
  return { channelUrl, messages, attempts };
}

// Reads run one after another on purpose. Two overlapping CDP calls into the same Discord session
// produced a composer-dirty refusal on a send and stale channel lists on reads, so callers get a
// serial helper rather than a Promise.all of readChannelEnd.
export async function readChannelSeries(ctx, args = {}) {
  const urls = args.urls || [];
  if (!urls.length) throw new Error('readChannelSeries needs urls');
  const out = [];
  for (const url of urls) {
    out.push(await readChannelEnd(ctx, { channelUrl: url, limit: args.limit, mask: args.mask }));
  }
  return out;
}
