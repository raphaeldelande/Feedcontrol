importScripts('taxonomy.js','classifier.js');
const C=FeedControlClassifier;let queue=Promise.resolve();let active=0;const waiting=[];const cache=new Map();
async function limited(fn){if(active>=3)await new Promise(r=>waiting.push(r));active++;try{return await fn();}finally{active--;waiting.shift()?.();}}
async function api(path,body){return limited(async()=>{const r=await fetch('http://127.0.0.1:8765'+path,{method:body?'POST':'GET',headers:{'Content-Type':'application/json'},...(body?{body:JSON.stringify(body)}:{}),signal:AbortSignal.timeout(12000)});const data=await r.json();if(!r.ok)throw Error(data.error||`Serveur : ${r.status}`);return data;});}
async function handle(m,sender){
 if(m.type==='FC_STATUS'){try{return await api('/');}catch{return {status:'offline',discovery:false,error:'Serveur local indisponible — lancer python ai_server.py'};}}
 if(m.type==='FC_CLASSIFY'){
  const key=m.video?.videoId+':'+m.video?.title;const old=cache.get(key);if(old&&old.until>Date.now())return old.value;
  let value;try{value=await api('/classify',m.video);}catch{value={...C.classify(m.video),degraded:true};}
  cache.set(key,{until:Date.now()+(value.degraded?30000:3600000),value});if(cache.size>500)cache.delete(cache.keys().next().value);return value;
 }
 if(m.type==='FC_DISCOVER')return api('/discover',{topics:m.topics,refresh:!!m.refresh});
 if(m.type==='FC_FEEDBACK'){
  const {feedback={}}=await chrome.storage.local.get('feedback');feedback[m.videoId]={verdict:m.verdict,at:Date.now()};
  const entries=Object.entries(feedback).sort((a,b)=>b[1].at-a[1].at).slice(0,500);await chrome.storage.local.set({feedback:Object.fromEntries(entries)});return {ok:true};
 }
 if(m.type==='FC_CLEAR'){await chrome.storage.local.remove(['statsV4','stats']);return {ok:true};}
 if(m.type==='FC_EVENT'){
  const raw=await chrome.storage.local.get(null),s=C.migrate(raw);if(!s.tracking)return {ok:true,tracking:false};
  const stats=raw.statsV4||{days:{}};const day=new Date().toISOString().slice(0,10);
  const d=stats.days[day]||{seconds:0,views:0,shortsSeconds:0,hidden:0,impressions:0,favoredSeconds:0,categories:{},seen:[]};
  const category=C.POSITIVE.includes(m.category)?m.category:'autre';const cat=d.categories[category]||{seconds:0,views:0};
  if(m.kind==='watch'){
   const seconds=Math.max(0,Math.min(5,Number(m.seconds)||0));d.seconds+=seconds;cat.seconds+=seconds;if(m.short)d.shortsSeconds+=seconds;if(s.favorites.includes(category))d.favoredSeconds+=seconds;
   if(seconds>0&&m.videoId&&!d.seen.includes(m.videoId)){d.seen.push(m.videoId);d.seen=d.seen.slice(-2000);d.views++;cat.views++;}
  }
  if(m.kind==='feed'){d.impressions++;if(m.hidden)d.hidden++;}
  d.categories[category]=cat;stats.days[day]=d;
  const cutoff=new Date(Date.now()-(s.retentionDays-1)*86400000).toISOString().slice(0,10);for(const key of Object.keys(stats.days))if(key<cutoff)delete stats.days[key];
  await chrome.storage.local.set({statsV4:stats});return {ok:true};
 }
 return {error:'Message inconnu'};
}
chrome.runtime.onMessage.addListener((m,sender,respond)=>{
 // Sérialiser les écritures empêche les mises à jour perdues entre onglets.
 const mutation=['FC_EVENT','FC_CLEAR','FC_FEEDBACK'].includes(m.type);
 const task=mutation?(queue=queue.catch(()=>{}).then(()=>handle(m,sender))):handle(m,sender);
 task.then(respond).catch(e=>respond({error:e.message}));return true;
});
chrome.runtime.onInstalled.addListener(async()=>{const raw=await chrome.storage.local.get(null);await chrome.storage.local.set(C.migrate(raw));});
