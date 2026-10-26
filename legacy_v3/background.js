const EMPTY=()=>({day:new Date().toLocaleDateString('en-CA'),feed:{},watched:{},seconds:0,impressions:0,hidden:0,views:0,shortsSeconds:0});
let queue=Promise.resolve();
function dayKey(){const d=new Date();return [d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-');}
chrome.runtime.onMessage.addListener((msg,sender,sendResponse)=>{
 if(msg.type!=='FC_EVENT')return;
 queue=queue.then(async()=>{
  const {stats}=await chrome.storage.local.get('stats');const s=stats&&stats.day===dayKey()?stats:{...EMPTY(),day:dayKey()};
  if(msg.kind==='feed'){s.feed[msg.category]=(s.feed[msg.category]||0)+1;s.impressions++;if(msg.hidden)s.hidden++;}
  if(msg.kind==='watch'){s.seconds+=Math.max(0,Math.min(10,Number(msg.seconds)||0));if(msg.short)s.shortsSeconds+=Math.max(0,Math.min(10,Number(msg.seconds)||0));s.watched[msg.category]=(s.watched[msg.category]||0)+Math.max(0,Math.min(10,Number(msg.seconds)||0));}
  if(msg.kind==='view')s.views++;
  await chrome.storage.local.set({stats:s});sendResponse({ok:true});
 }).catch(()=>sendResponse({ok:false}));return true;
});

// Optional local semantic classifier: no third-party API keys or YouTube API.
chrome.runtime.onMessage.addListener((msg,sender,respond)=>{
 if(msg.type!=="FC_CLASSIFY")return false;
 fetch("http://127.0.0.1:8765/classify",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({title:msg.title}),signal:AbortSignal.timeout(15000)})
  .then(r=>{if(!r.ok)throw Error("server unavailable");return r.json()})
  .then(res=>respond(res)).catch(()=>respond({error:"AI offline"}));
 return true;
});
