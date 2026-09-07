import test from 'node:test';
import assert from 'node:assert/strict';
import { definitions, attach, locked, reflectionRequest, registerCrew } from './crew.mjs';
import { mkdtemp } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

function fakePi(){
 const handlers={},commands={};
 return { handlers,commands,
  on:(n,f)=>{(handlers[n]??=[]).push(f);},
  events:{emit:()=>{},on:(n,f)=>{(handlers['evt:'+n]??=[]).push(f);}},
  registerCommand:(n,c)=>{commands[n]=c;} };
}
function recordingCall(rows=[]){
 const calls=[];
 const call=async(ref,args)=>{ calls.push([ref,args]);
  if(ref==='agents.self') return {kind:'root',rootId:'session:abc',ownerHostId:'session:abc',cwd:'/nowhere'};
  if(ref==='agents.actors') return rows;
  if(ref==='agents.create') { const row={name:args.name,id:'new-'+args.name,status:'idle',rootId:'session:abc',...args}; rows.push(row); return row; }
  if(ref==='agents.ask') return {actorId:args.id,direction:'out',action:'silent'};
  if((ref==='agents.tell'||ref==='agents.ask')) return {queued:true};
  if(ref.startsWith('extensions.')) return {details:{results:[],documentId:'doc-1'}};
  throw Error('unexpected '+ref); };
 return {call,calls};
}
async function activatedCrew(rows=[],env={},trusted=true){
 const root=await mkdtemp(join(tmpdir(),'crew-h-'));
 const f=recordingCall(rows);
 const p=fakePi();
 const {component,status,drain}=registerCrew(p,{configDir:'.pi',sharedRoot:'/shared',env});
 await component.activate({signal:new AbortController().signal,call:f.call,guide:()=>()=>{},invocation:{extensionContext:{isProjectTrusted:()=>trusted,cwd:root,sessionManager:{getSessionId:()=>'main-sess'},model:{provider:'prov',id:'m1'}}}},{});
 return {p,f,status,root,handler:async (...args)=>{await p.handlers.session_compact?.[0](...args); await drain();}};
}
const compactCtx={sessionManager:{getSessionId:()=>'sess-9'},isProjectTrusted:()=>true};

const D=definitions('/p1','/shared','prov/m');

test('six roles, unique names, native durable contract',()=>{
 assert.equal(D.length,6);
 assert.equal(new Set(D.map(d=>d.name)).size,6);
 for(const d of D){ assert.equal(d.runner,'pi'); assert.equal(d.residency,'durable'); assert.equal(d.responseMode,'directive'); }
 assert.equal(D[0].triggerTurn,true); // supervisor only
 assert.equal(D[5].delivery,'mailbox'); assert.deepEqual(D[5].events,[]); // reflector: component-driven
 assert.ok(D[2].tools.includes('bash')); assert.ok(!D[4].tools.includes('edit'));
});

function fakeCall(rows=[],created=[]){
 const calls=[];
 const call=async(ref,args)=>{ calls.push([ref,args]);
  if(ref==='agents.actors') return rows;
  if(ref==='agents.create'){ const a={id:'new-'+created.length,name:args.name,status:'idle',rootId:'session:abc',...args}; created.push(a); return a; }
  throw Error('unexpected '+ref); };
 return {call,calls,created};
}

test('attach reuses idle actors without replacement and creates missing ones',async()=>{
 const old={name:'project-scout',id:'s1',status:'idle'};
 const f=fakeCall([old]);
 const r=await attach(f.call,D);
 assert.equal(r.length,6);
 const scout=r.find(x=>x.actor.name==='project-scout');
 assert.equal(scout.reused,true); assert.equal(scout.actor.id,'s1');
 assert.ok(r.filter(x=>!x.reused).length===5 && f.created.length===5);
});

test('attach refuses duplicate existing names and stopped actors before creating anything',async()=>{
 const row=n=>({name:n,id:'x',status:'idle'});
 const f1=fakeCall([row('project-scout'),{...row('project-scout'),id:'y'}]);
 await assert.rejects(attach(f1.call,D),/Ambiguous actor project-scout/); assert.equal(f1.created.length,0);
 const f2=fakeCall([{name:'project-verifier',id:'v',status:'running'}]);
 await assert.rejects(attach(f2.call,D),/project-verifier is running/); assert.equal(f2.created.length,0);
 const f3=fakeCall([{name:'project-verifier',id:'v',status:'stopped'}]);
 await assert.rejects(attach(f3.call,D),/project-verifier is stopped/); assert.equal(f3.created.length,0);
});

test('attach rejects duplicate desired definitions up front',async()=>{
 const f=fakeCall();
 await assert.rejects(attach(f.call,[...D,D[0]]),/Duplicate desired actor names/); assert.equal(f.created.length,0);
});

test('install lock serializes and releases',async()=>{
 const fs=await import('node:fs/promises');
 const dir=await fs.mkdtemp('/tmp/crew-lock-');
 let inside=0,maxInside=0;
 await Promise.all([1,2,3].map(()=>locked(dir,'.pi',async()=>{
  inside++; maxInside=Math.max(maxInside,inside); await new Promise(r=>setTimeout(r,20)); inside--; })));
 assert.equal(maxInside,1);
 await fs.mkdir(`${dir}/.pi/fabric/crew-install.lock`); // simulate a held lock
 await assert.rejects(locked(dir,'.pi',async()=>{}),/lock busy|Crew install lock/);
});

test('session_compact handler queues exactly-once reflection with exact ids',async()=>{
 const {f,handler}=await activatedCrew();
 const event={compactionEntry:{id:'cp-1'}};
 await handler(event,compactCtx);
 const tells=f.calls.filter(([ref])=>(ref==='agents.tell'||ref==='agents.ask'));
 // legacy reflector + auto reflector + auto foundation
 assert.equal(tells.length,3);
 assert.equal(tells[0][1].id,'new-session-reflector');
 assert.match(tells[0][1].message,/sessionId=sess-9/); assert.match(tells[0][1].message,/checkpointId=cp-1/);
 assert.equal(tells[0][1].data.sessionId,'sess-9'); assert.equal(tells[0][1].data.checkpointId,'cp-1');
 assert.match(tells[1][1].message,/AUTO reflector .*checkpoint=cp-1/);
 assert.match(tells[2][1].message,/AUTO foundation .*checkpoint=cp-1/);
 await handler(event,compactCtx);
 assert.equal(f.calls.filter(([r])=>(r==='agents.tell'||r==='agents.ask')).length,3); // duplicate checkpoint deduped everywhere
 await handler({compactionEntry:{id:'cp-2'}},compactCtx);
 assert.equal(f.calls.filter(([r])=>(r==='agents.tell'||r==='agents.ask')).length,6); // new checkpoint queues again
});

test('session_compact handler defers to a legacy natively-subscribed reflector',async()=>{
 const legacy={name:'session-reflector',id:'refl-1',status:'idle',rootId:'session:abc',events:['session_compact']};
 const {f,handler,status}=await activatedCrew([legacy]);
 await handler({compactionEntry:{id:'cp-1'}},compactCtx);
 // legacy reflector suppressed; only auto reflector + auto foundation queue
 assert.equal(f.calls.filter(([r])=>(r==='agents.tell'||r==='agents.ask')).length,2);
 assert.equal(status().legacyReflection,true);
});

test('crew skips fabric children and untrusted projects before any actor call',async()=>{
 const child=await activatedCrew([],{PI_FABRIC_ACTOR_ID:'a1'});
 assert.equal(child.f.calls.length,0); assert.equal(child.status().state,'skipped');
 await child.handler({compactionEntry:{id:'cp'}},compactCtx);
 assert.equal(child.f.calls.filter(([r])=>(r==='agents.tell'||r==='agents.ask')).length,0);
 const untrusted=await activatedCrew([],{},false);
 assert.equal(untrusted.f.calls.length,0); assert.equal(untrusted.status().state,'skipped');
});

test('crew-model pins session-scope model on legacy plus auto actors, tolerates per-actor errors, clear omits model',async()=>{
 const rows=D.map((d,i)=>({name:d.name,id:'id-'+i,status:'idle'}));
 const calls=[];
 const call=async(ref,args)=>{calls.push([ref,args]);
  if(ref==='agents.self')return {kind:'root',rootId:'session:abc',ownerHostId:'session:abc'};
  if(ref==='agents.actors')return rows;
  if(ref==='agents.create')return {name:args.name,id:'new-'+args.name,status:'idle'};
  if(ref==='agents.setModel'){if(args.id==='id-3')throw Error('boom');return {};}
  if(ref.startsWith('extensions.'))return {details:{results:[],documentId:'d'}};
  throw Error('unexpected '+ref);};
 const root=await mkdtemp(join(tmpdir(),'crew-cm-'));
 const commands=[],notices=[];
 const p={events:{emit:()=>{},on:()=>{}},on:()=>{},registerCommand:(n,c)=>{commands.push(c);}};
 const {component}=registerCrew(p,{configDir:'.pi',sharedRoot:'/shared',env:{}});
 await component.activate({signal:new AbortController().signal,call,guide:()=>()=>{},invocation:{extensionContext:{isProjectTrusted:()=>true,cwd:root,sessionManager:{getSessionId:()=>'s'},model:{provider:'prov',id:'m1'}}}},{})
 const h=commands.find(c=>c.description.startsWith('Pin or clear'));assert.ok(h,'crew-model registered');
 await h.handler('',{ui:{notify:(...a)=>notices.push(a)}});
 assert.match(notices.at(-1)[0],/Usage:/);assert.equal(calls.filter(([r])=>r==='agents.setModel').length,0);
 await h.handler('prov/m2',{ui:{notify:(...a)=>notices.push(a)}});
 const sets=calls.filter(([r])=>r==='agents.setModel');
 assert.equal(sets.length,12); // six legacy + six auto
 assert.ok(sets.every(([,a])=>a.scope==='session'&&a.model==='prov/m2'));
 assert.match(notices.at(-1)[0],/id-3: Error: boom/);assert.match(notices.at(-1)[0],/new-auto-s: ok/);
 await h.handler('clear',{ui:{notify:(...a)=>notices.push(a)}});
 const clears=calls.filter(([r])=>r==='agents.setModel').slice(-12);
 assert.ok(clears.every(([,a])=>a.scope==='session'&&!('model' in a)));
 const commands2=[];const p2={events:{emit:()=>{},on:()=>{}},on:()=>{},registerCommand:(n,c)=>{commands2.push(c);}};
 registerCrew(p2,{configDir:'.pi',sharedRoot:'/shared',env:{}}); // never activated
 await commands2.find(c=>c.description.startsWith('Pin or clear')).handler('prov/m2',{ui:{notify:(...a)=>notices.push(a)}});
 assert.match(notices.at(-1)[0],/not active/);
 assert.equal(calls.filter(([r])=>r==='agents.setModel').length,24);
});

test('reflection request pins exact session and checkpoint ids',()=>{
 const ctx={cwd:'/p1',sessionManager:{getSessionId:()=>'sess-1'}};
 const req=reflectionRequest(ctx,{compactionEntry:{id:'cp-9'}});
 assert.match(req.message,/sessionId=sess-1/); assert.match(req.message,/checkpointId=cp-9/);
 assert.equal(req.data.sessionId,'sess-1'); assert.equal(req.data.checkpointId,'cp-9');
 assert.throws(()=>reflectionRequest(ctx,{}),/checkpoint/);
});
