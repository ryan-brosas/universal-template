// Discord web: post a native threaded reply, or dry-run the sequence.
//
// Derived from live work on 2026-09-25 in largish public servers. The parts that
// are easy to get wrong are all encoded here: the hover toolbar only renders
// for a real CDP mouse move over a message that is scrolled into view, the Reply
// control is a plain click target rather than a link, reply mode is detectable
// through a replybar class, and the sent row is often outside the rendered window
// at a permalink anchor so confirmation has to happen at the channel end first.

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export async function replyToMessage(ctx, args = {}) {
  const session = ctx?.session;
  if (!session) throw new Error('reply_to_message needs an active CDP session in ctx.session');
  const { channelUrl, messageId, text, dryRun = false, targetId: reuseTargetId } = args;
  if (!channelUrl || !messageId) throw new Error('channelUrl and messageId are required');
  if (!dryRun && !text) throw new Error('text is required unless dryRun is set');

  const call = ctx.cdp || ((sid, method, params = {}) => session._call(method, params, { sessionId: sid }));
  const J = JSON.stringify;
  // Reuse an owned tab when the caller passes targetId. Opening and closing a tab per reply is
  // visible churn in a browser the user is watching, and it throws away a warm channel page.
  const target = reuseTargetId ? { targetId: reuseTargetId } : await session.Target.createTarget({ url: 'about:blank', background: true });
  const ownsTab = !reuseTargetId;
  const attached = await session.Target.attachToTarget({ targetId: target.targetId, flatten: true });
  const sessionId = attached.sessionId;
  const evaluate = async (expression) => {
    const r = await call(sessionId, 'Runtime.evaluate', { expression, returnByValue: true });
    return r?.result?.value ? JSON.parse(r.result.value) : null;
  };
  const evidence = {};
  try {
    await call(sessionId, 'Page.enable', {});
    if (session.Target.activateTarget) await session.Target.activateTarget({ targetId: target.targetId });
    await call(sessionId, 'Page.bringToFront', {}).catch(() => {});
    await call(sessionId, 'Page.navigate', { url: `${channelUrl}/${messageId}` });

    const prep = `((id,text)=>{const el=document.getElementById('message-content-'+id);const comp=document.querySelector('[class*=channelTextArea] [role=textbox]');if(!el)return JSON.stringify({ready:false});el.scrollIntoView({block:'center'});const r=el.getBoundingClientRect();const dup=[...document.querySelectorAll('[id^=message-content-]')].filter(e=>e.textContent.trim()===text).length;return JSON.stringify({ready:true,x:Math.round(r.left+r.width*0.5),y:Math.round(r.top+r.height*0.5),composerEmpty:comp?(comp.textContent||'').replace(/\uFEFF/g,'').trim().length===0:false,dup});})(${J(messageId)},${J(text || '')})`;
    let info = null;
    for (let i = 0; i < 100; i++) {
      await sleep(320);
      try { info = await evaluate(prep); } catch {}
      if (info?.ready) break;
    }
    if (!info?.ready) return { stage: 'target-missing', targetId: target.targetId, evidence };
    await sleep(600);
    info = await evaluate(prep) || info;
    evidence.sourceCentered = true;
    evidence.composerWasEmpty = info.composerEmpty;
    if (info.dup > 0) return { stage: 'already-present', targetId: target.targetId, evidence };
    if (!info.composerEmpty) return { stage: 'composer-dirty', targetId: target.targetId, evidence };

    const replyControl = `((id)=>{const src=document.getElementById('message-content-'+id);const row=src?src.closest('[id^=chat-messages-]'):null;if(!row)return JSON.stringify({ok:false,why:'no-row'});const b=[...row.querySelectorAll('button,[role=button]')].find(x=>/^reply$/i.test(x.getAttribute('aria-label')||''));if(!b)return JSON.stringify({ok:false,why:'no-reply-button'});b.click();return JSON.stringify({ok:true});})(${J(messageId)})`;
    // The reply bar names the author being replied to, not the message text, so verify the
    // author of the source row rather than trying to match the quoted body.
    const replyMode = `((id)=>{const src=document.getElementById('message-content-'+id);const row=src?src.closest('[id^=chat-messages-]'):null;const author=(()=>{const list=row?[...row.querySelectorAll('[class*=username]')].filter(x=>!x.closest('[class*=repliedMessage]')):[];const u=list[0];return u?u.textContent.trim():'';})();const el=[...document.querySelectorAll('*')].find(e=>/replybar/i.test(String(e.className||''))&&!/replied/i.test(String(e.className||'')));const barText=el?el.textContent.trim().slice(0,140):'';const comp=document.querySelector('[class*=channelTextArea] [role=textbox]');return JSON.stringify({replyMode:!!el,barText,authorMatches:author?barText.indexOf(author)>=0:null,composerEmpty:comp?(comp.textContent||'').replace(/\uFEFF/g,'').trim().length===0:false});})(${J(messageId)})`;

    await call(sessionId, 'Input.dispatchMouseEvent', { type: 'mouseMoved', x: info.x, y: info.y, buttons: 0 });
    await sleep(600);
    await call(sessionId, 'Input.dispatchMouseEvent', { type: 'mouseMoved', x: info.x + 2, y: info.y + 1, buttons: 0 });
    await sleep(1000);
    let clicked = await evaluate(replyControl);
    await sleep(1300);
    let mode = await evaluate(replyMode);
    if (!mode?.replyMode) {
      await sleep(600);
      clicked = await evaluate(replyControl);
      await sleep(1300);
      mode = await evaluate(replyMode);
    }
    evidence.replyControl = clicked;
    evidence.replyMode = mode;
    if (!mode?.replyMode) return { stage: 'reply-mode-failed', targetId: target.targetId, evidence };
    if (mode.authorMatches === false) return { stage: 'wrong-source-author', targetId: target.targetId, evidence };

    const focus = `(()=>{const c=document.querySelector('[class*=channelTextArea] [role=textbox]');if(!c)return JSON.stringify({focused:false});c.focus();return JSON.stringify({focused:document.activeElement===c});})()`;
    const composer = `(()=>{const c=document.querySelector('[class*=channelTextArea] [role=textbox]');return JSON.stringify({text:c?c.textContent:'',empty:c?(c.textContent||'').replace(/\uFEFF/g,'').trim().length===0:false});})()`;
    const fc = await evaluate(focus);
    if (!fc?.focused) return { stage: 'composer-focus-failed', targetId: target.targetId, evidence };

    if (dryRun) {
      const probe = text || 'dry run probe';
      await call(sessionId, 'Input.insertText', { text: probe });
      await sleep(500);
      const typed = await evaluate(composer);
      evidence.dryRunTyped = typed?.text?.trim() === probe;
      // Clearing needs a genuine caret. Selection-only edits, execCommand and Backspace
      // without a click are reverted by the editor on its next render, and Escape cancels
      // reply mode but leaves the text. A real click into the composer plus Ctrl+A and
      // Backspace is what actually empties it.
      const rect = `(()=>{const c=document.querySelector('[class*=channelTextArea] [role=textbox]');if(!c)return JSON.stringify({ok:false});const r=c.getBoundingClientRect();return JSON.stringify({ok:true,x:Math.round(r.left+r.width*0.5),y:Math.round(r.top+r.height*0.5)});})()`;
      const box = await evaluate(rect);
      if (box?.ok) {
        await call(sessionId, 'Input.dispatchMouseEvent', { type: 'mouseMoved', x: box.x, y: box.y, buttons: 0 });
        await sleep(200);
        await call(sessionId, 'Input.dispatchMouseEvent', { type: 'mousePressed', x: box.x, y: box.y, button: 'left', buttons: 1, clickCount: 1 });
        await call(sessionId, 'Input.dispatchMouseEvent', { type: 'mouseReleased', x: box.x, y: box.y, button: 'left', buttons: 0, clickCount: 1 });
        await sleep(400);
        await call(sessionId, 'Input.dispatchKeyEvent', { type: 'rawKeyDown', key: 'a', code: 'KeyA', modifiers: 2, windowsVirtualKeyCode: 65, nativeVirtualKeyCode: 65 });
        await call(sessionId, 'Input.dispatchKeyEvent', { type: 'keyUp', key: 'a', code: 'KeyA', modifiers: 2, windowsVirtualKeyCode: 65, nativeVirtualKeyCode: 65 });
        await sleep(250);
        await call(sessionId, 'Input.dispatchKeyEvent', { type: 'rawKeyDown', key: 'Backspace', code: 'Backspace', windowsVirtualKeyCode: 8, nativeVirtualKeyCode: 8 });
        await call(sessionId, 'Input.dispatchKeyEvent', { type: 'keyUp', key: 'Backspace', code: 'Backspace', windowsVirtualKeyCode: 8, nativeVirtualKeyCode: 8 });
        await sleep(500);
      }
      await call(sessionId, 'Input.dispatchKeyEvent', { type: 'keyDown', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27, nativeVirtualKeyCode: 27 });
      await call(sessionId, 'Input.dispatchKeyEvent', { type: 'keyUp', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27, nativeVirtualKeyCode: 27 });
      await sleep(600);
      const after = await evaluate(composer);
      evidence.dryRunCleared = !!after?.empty;
      evidence.dryRunSubmittedNothing = true;
      return { stage: after?.empty ? 'dry-run' : 'dry-run-dirty', targetId: target.targetId, evidence };
    }

    await call(sessionId, 'Input.insertText', { text });
    await sleep(600);
    const typed = await evaluate(composer);
    evidence.typedExact = typed?.text?.trim() === text;
    if (!evidence.typedExact) {
      // Leave the composer as we found it: an aborted attempt must not strand a draft in a channel
      // the user shares. Same clear sequence as the dry-run path, then report what happened.
      const rect = `(()=>{const c=document.querySelector('[class*=channelTextArea] [role=textbox]');if(!c)return JSON.stringify({ok:false});const r=c.getBoundingClientRect();return JSON.stringify({ok:true,x:Math.round(r.left+r.width*0.5),y:Math.round(r.top+r.height*0.5)});})()`;
      const box = await evaluate(rect);
      if (box?.ok) {
        await call(sessionId, 'Input.dispatchMouseEvent', { type: 'mouseMoved', x: box.x, y: box.y, buttons: 0 });
        await sleep(200);
        await call(sessionId, 'Input.dispatchMouseEvent', { type: 'mousePressed', x: box.x, y: box.y, button: 'left', buttons: 1, clickCount: 1 });
        await call(sessionId, 'Input.dispatchMouseEvent', { type: 'mouseReleased', x: box.x, y: box.y, button: 'left', buttons: 0, clickCount: 1 });
        await sleep(400);
        await call(sessionId, 'Input.dispatchKeyEvent', { type: 'rawKeyDown', key: 'a', code: 'KeyA', modifiers: 2, windowsVirtualKeyCode: 65, nativeVirtualKeyCode: 65 });
        await call(sessionId, 'Input.dispatchKeyEvent', { type: 'keyUp', key: 'a', code: 'KeyA', modifiers: 2, windowsVirtualKeyCode: 65, nativeVirtualKeyCode: 65 });
        await sleep(250);
        await call(sessionId, 'Input.dispatchKeyEvent', { type: 'rawKeyDown', key: 'Backspace', code: 'Backspace', windowsVirtualKeyCode: 8, nativeVirtualKeyCode: 8 });
        await call(sessionId, 'Input.dispatchKeyEvent', { type: 'keyUp', key: 'Backspace', code: 'Backspace', windowsVirtualKeyCode: 8, nativeVirtualKeyCode: 8 });
        await sleep(500);
      }
      const after = await evaluate(composer);
      evidence.cleanupCleared = !!after?.empty;
      return { stage: 'typed-mismatch', targetId: target.targetId, evidence };
    }

    await call(sessionId, 'Input.dispatchKeyEvent', { type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, nativeVirtualKeyCode: 13, text: '\r', unmodifiedText: '\r' });
    await call(sessionId, 'Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, nativeVirtualKeyCode: 13 });
    await sleep(3200);

    await call(sessionId, 'Page.navigate', { url: channelUrl });
    await sleep(5000);
    const scan = `((text)=>{const rows=[...document.querySelectorAll('li[id^=chat-messages-]')].slice(-14);const hits=rows.filter(li=>{const id=li.id.split('-').pop();const own=li.querySelector('[id=message-content-'+id+']');return own&&own.textContent.trim()===text;});return JSON.stringify(hits.map(li=>{const id=li.id.split('-').pop();const t=li.querySelector('time');const q=li.querySelector('[class*=repliedMessage] [id^=message-content-]');return {id,time:t?t.getAttribute('datetime'):'',quoted:q?q.textContent.trim().slice(0,120):''};}));})(${J(text)})`;
    let found = null;
    for (let i = 0; i < 8; i++) {
      try { found = await evaluate(scan); } catch {}
      if (found?.length) break;
      await sleep(1200);
    }
    if (!found?.length) return { stage: 'unresolved', targetId: target.targetId, evidence };
    evidence.channelEndHit = found[0];

    const permalink = `${channelUrl}/${found[0].id}`;
    await call(sessionId, 'Page.navigate', { url: permalink });
    await sleep(4000);
    const verify = `((id,text)=>{const own=document.getElementById('message-content-'+id);const row=own?own.closest('li'):null;const q=row?row.querySelector('[class*=repliedMessage] [id^=message-content-]'):null;const t=row?row.querySelector('time'):null;const panel=document.querySelector('[class*=panels] [class*=nameTag]');const labels=(panel?panel.innerText:'').split(String.fromCharCode(10)).map(x=>x.trim().toLowerCase()).filter(Boolean);return JSON.stringify({present:!!own,exact:own?own.textContent.trim()===text:false,quoted:q?q.textContent.trim().slice(0,120):'',time:t?t.getAttribute('datetime'):'',accounts:labels.slice(0,2)});})(${J(found[0].id)},${J(text)})`;
    let checked = null;
    for (let i = 0; i < 80; i++) {
      await sleep(320);
      try { checked = await evaluate(verify); } catch {}
      if (checked?.present) break;
    }
    evidence.permalinkChecked = checked;
    return { stage: checked?.exact ? 'sent' : 'unresolved', targetId: target.targetId, sentId: found[0].id, permalink, evidence };
  } finally {
    if (ownsTab) session.closeTab(target.targetId, sessionId).catch(() => {});
    else if (session.Target.detachFromTarget) session.Target.detachFromTarget({ sessionId }).catch(() => {});
  }
}
