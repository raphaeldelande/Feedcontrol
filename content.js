(()=>{
 const C=FeedControlClassifier;
 // Filtrage limité à l'accueil. Aucun contrôle du lecteur, des publicités ou des autres pages.
 const CARD='ytd-rich-item-renderer,ytd-video-renderer,ytd-grid-video-renderer,yt-lockup-view-model,ytd-reel-item-renderer,ytd-shorts-lockup-view-model';
 const TITLE='#video-title,#video-title-link,.yt-lockup-metadata-view-model__title,h3 a,h3';
 let nativeSignature='',shownDiscoveries=[],s=C.migrate({}),feedback={},timer,generation=0,page='',results=new Map(),pending=new Set(),seen=new Set(),recent={},discoveryKey='',requestVersion=0,discoverVideos=[],lastSample=null,lastTick=performance.now(),watchBuffer=null;
 const home=()=>location.pathname==='/'||location.pathname==='/feed/subscriptions';
 const send=m=>chrome.runtime.sendMessage(m).catch(()=>({error:'Extension indisponible : rechargez cet onglet.'}));
 function videoId(url){try{const u=new URL(url,location.origin);return u.searchParams.get('v')||u.pathname.match(/^\/shorts\/([\w-]+)/)?.[1]||'';}catch{return '';}}
 function schedule(){clearTimeout(timer);timer=setTimeout(apply,220);}
 function panel(){let p=document.getElementById('feedcontrol-panel');if(!p){p=document.createElement('section');p.id='feedcontrol-panel';p.setAttribute('aria-label','Découvertes FeedControl');const target=document.querySelector('ytd-browse[page-subtype="home"] #primary,ytd-browse #primary,ytd-rich-grid-renderer')||document.querySelector('ytd-browse');target?.prepend(p);}return p;}
 function node(tag,text,cls){const e=document.createElement(tag);if(text)e.textContent=text;if(cls)e.className=cls;return e;}
 function renderDiscovery(message=''){
  if(!home()||!s.enabled||!s.discovery){document.getElementById('feedcontrol-panel')?.remove();return;}
  const root=panel();const expanded=new Set([...root.querySelectorAll('details[open]')].map(e=>e.dataset.videoId));root.replaceChildren();const head=node('div',null,'fc-heading');head.append(node('h2','✦ Découvertes FeedControl'),node('span','Sélection indépendante · vidéos YouTube'));
  const more=node('button','Explorer d’autres vidéos');more.onclick=()=>discover(true);head.append(more);root.append(head);
  root.append(node('p',message||'Titres et miniatures YouTube inchangés. Analyse du texte uniquement.','fc-message'));
  const grid=node('div',null,'fc-grid');const nativeIds=new Set([...document.querySelectorAll(CARD)].map(card=>videoId(card.querySelector('a[href*="watch?v="],a[href*="/shorts/"]')?.href)));
  const ranked=discoverVideos.filter(v=>!nativeIds.has(v.videoId)).map(v=>C.decide(v,s,s.shortsOff&&C.potentialShort(v),feedback[v.videoId])).filter(v=>v.visible&&v.favored).map(v=>({...v,rank:v.rank-(recent[v.videoId]? .4:0)})).sort((a,b)=>b.rank-a.rank);
  // Diversité : premier tour une vidéo par catégorie primaire, puis compléter.
  const chosen=[],used=new Set();for(const v of ranked)if(!used.has(v.category)){chosen.push(v);used.add(v.category);}for(const v of ranked)if(!chosen.includes(v))chosen.push(v);
  shownDiscoveries=[];
  for(const v of chosen.slice(0,12)){
   if(!/^[\w-]{11}$/.test(v.videoId))continue;
   shownDiscoveries.push(v.videoId);
   const card=node('article',null,'fc-card'),a=node('a');a.href='https://www.youtube.com/watch?v='+v.videoId;
   if(v.thumbnail){try{const url=new URL(v.thumbnail);if(url.protocol==='https:'&&(/(^|\.)ytimg\.com$/.test(url.hostname))){const img=node('img');img.src=url.href;img.alt='';img.loading='lazy';a.append(img);}}catch{}}
   a.append(node('h3',v.title));card.append(a,node('p',v.channelTitle||'YouTube'));
   const why=node('details'),summary=node('summary','Pourquoi cette vidéo ?');why.dataset.videoId=v.videoId;why.open=expanded.has(v.videoId);why.append(summary,node('p',v.recommendationReasons.join(' · ')+' · '+v.limitations+(v.subscriberCount==null?' · Abonnés inconnus':'')));
   for(const [verdict,label] of [['relevant','Pertinente'],['irrelevant','Pas pertinente'],['wrong','Mauvaise classification']]){const b=node('button',label);b.setAttribute('aria-pressed',String(feedback[v.videoId]?.verdict===verdict));b.onclick=async()=>{const response=await send({type:'FC_FEEDBACK',videoId:v.videoId,verdict});if(!response.error){feedback[v.videoId]={verdict};renderDiscovery('Votre retour ajuste le classement local ; aucun réentraînement.');}};why.append(b);}
   card.append(why);grid.append(card);
  }
  root.append(grid);if(!grid.children.length&&!message)root.append(node('p','Aucun résultat correspondant trouvé. Modifiez vos thèmes ou votre exigence de qualité.'));
 }
 async function discover(refresh=false){
  if(!s.discovery||!s.enabled||!home())return;
  const key=JSON.stringify([s.favorites,s.mode,s.blocked,s.quality,s.qualityLevel,s.smallCreators,s.subscriberThreshold]);
  if(!refresh&&discoveryKey===key)return;discoveryKey=key;
  if(!s.favorites.length){renderDiscovery('Choisissez un thème dans le popup pour découvrir des vidéos.');return;}
  const version=++requestVersion;renderDiscovery('Recherche de vidéos YouTube…');
  const response=await send({type:'FC_DISCOVER',topics:s.favorites,refresh});
  if(version!==requestVersion||!home()||!s.discovery||!s.enabled)return;
  if(response.error){discoverVideos=[];renderDiscovery(response.error);return;}
  discoverVideos=response.videos||[];renderDiscovery(response.message);
  // Historique limité d'exposition, indépendant du suivi de visionnage, sans données envoyées.
  if(shownDiscoveries.length){for(const id of shownDiscoveries)recent[id]=Date.now();recent=Object.fromEntries(Object.entries(recent).filter(([,t])=>Date.now()-t<7*86400000).slice(-300));await chrome.storage.local.set({recentDiscoveries:recent});}
 }
 function restore(){document.querySelectorAll('.feedcontrol-hidden').forEach(e=>e.classList.remove('feedcontrol-hidden'));document.querySelectorAll('[data-feedcontrol-order]').forEach(e=>{e.style.order=e.dataset.feedcontrolOrder;delete e.dataset.feedcontrolOrder;});}
 function apply(){
  if(page!==location.href){page=location.href;generation++;requestVersion++;results.clear();pending.clear();seen.clear();discoveryKey='';discoverVideos=[];lastSample=null;restore();}
  if(!home()||!s.enabled){restore();document.getElementById('feedcontrol-panel')?.remove();document.getElementById('feedcontrol-notice')?.remove();return;}
  const nativeIdsThisPass=[];let visible=0,hidden=0,compatible=0,unknown=0,degraded=false;const myGeneration=generation;
  for(const card of document.querySelectorAll(CARD)){
   if(card.closest('#feedcontrol-panel')||card.parentElement?.closest(CARD)||card.querySelector('ytd-ad-slot-renderer,ytd-display-ad-renderer'))continue;
   const a=card.querySelector('a[href*="watch?v="],a[href*="/shorts/"]'),id=videoId(a?.href);if(!id)continue;nativeIdsThisPass.push(id);
   const el=card.querySelector(TITLE),title=(el?.getAttribute('title')||el?.textContent||a?.getAttribute('title')||'').trim();if(!title)continue;
   const isShort=!!a.href.includes('/shorts/'),key=id+':'+title,video={videoId:id,title,source:'youtube_dom'};
   let v=results.get(key);if(!v){v=C.classify(video);if(!pending.has(key)&&pending.size<3){pending.add(key);send({type:'FC_CLASSIFY',video}).then(r=>{if(myGeneration===generation){results.set(key,r.error?{...v,degraded:true}:r);if(results.size>500)results.delete(results.keys().next().value);schedule();}pending.delete(key);});}}
   const decision=C.decide(v,s,isShort,feedback[id]);card.classList.toggle('feedcontrol-hidden',!decision.visible);if(!v.topics?.length)unknown++;if(v.degraded)degraded=true;
   if(!Object.hasOwn(card.dataset,'feedcontrolOrder'))card.dataset.feedcontrolOrder=card.style.order||'';
   const order=String(s.mode==='favor'&&decision.favored?-1:0);if(card.style.order!==order)card.style.order=order;
   decision.visible?visible++:hidden++;if(decision.visible&&decision.favored)compatible++;
   if(!seen.has(id)){seen.add(id);if(seen.size>2000)seen.delete(seen.values().next().value);send({type:'FC_EVENT',kind:'feed',category:decision.category,hidden:!decision.visible});}
  }
  for(const shelf of document.querySelectorAll('ytd-rich-shelf-renderer[is-shorts],ytd-reel-shelf-renderer'))shelf.classList.toggle('feedcontrol-hidden',s.shortsOff);
  let notice=document.getElementById('feedcontrol-notice');if(!notice){notice=node('div');notice.id='feedcontrol-notice';notice.setAttribute('role','status');document.body.append(notice);}
  const text=`FeedControl · ${visible} visibles · ${hidden} masquées · ${unknown} thèmes inconnus${degraded?' · Serveur indisponible : heuristique locale':''}${s.mode==='only'?' · Inconnues non validées':''}`;if(notice.textContent!==text)notice.textContent=text;
  const nextSignature=nativeIdsThisPass.sort().join(',');if(nextSignature!==nativeSignature){nativeSignature=nextSignature;if(discoverVideos.length)renderDiscovery();}
  if(s.discovery){if(compatible<s.feedThreshold||document.getElementById('feedcontrol-panel'))discover();else renderDiscovery('Votre flux contient suffisamment de vidéos. Vous pouvez explorer manuellement.');}else document.getElementById('feedcontrol-panel')?.remove();
 }
 function flushWatch(){if(watchBuffer?.seconds>0)send({type:'FC_EVENT',kind:'watch',...watchBuffer});watchBuffer=null;}
 function sample(){
  const now=performance.now(),wall=(now-lastTick)/1000;lastTick=now;
  const id=videoId(location.href),player=document.querySelector('video.html5-main-video');
  const title=document.querySelector('h1.ytd-watch-metadata,h2.ytd-reel-player-header-renderer')?.textContent||document.title;
  const current={id,time:player?.currentTime||0,rate:player?.playbackRate||1,active:!!(s.tracking&&id&&player&&!player.paused&&!player.ended&&!player.seeking&&!document.hidden&&player.readyState>=2&&!document.querySelector('.html5-video-player.ad-showing'))};
  const delta=C.watchDelta(lastSample,current,wall);lastSample=current;
  if(!s.tracking){watchBuffer=null;return;}
  if(watchBuffer&&watchBuffer.videoId!==id)flushWatch();
  if(delta>0){if(!watchBuffer)watchBuffer={videoId:id,category:C.classify(title).category,short:location.pathname.startsWith('/shorts/'),seconds:0};watchBuffer.seconds+=delta;}
  if(watchBuffer?.seconds>=4||!current.active)flushWatch();
 }
 chrome.storage.local.get(null).then(raw=>{s=C.migrate(raw);feedback=raw.feedback||{};recent=raw.recentDiscoveries||{};schedule();});
 chrome.storage.onChanged.addListener((changes,area)=>{
  if(area!=='local')return;let changed=false;for(const k of Object.keys(C.DEFAULTS))if(changes[k]){s[k]=changes[k].newValue;changed=true;}
  if(changes.feedback){feedback=changes.feedback.newValue||{};changed=true;}
  if(changes.statsV4&&!changes.statsV4.newValue){watchBuffer=null;lastSample=null;seen.clear();}
  if(changed){s=C.migrate(s);requestVersion++;discoveryKey='';schedule();if(s.discovery&&home())renderDiscovery();}
 });
 new MutationObserver(records=>{if(records.some(r=>!r.target.closest?.('#feedcontrol-panel,#feedcontrol-notice')&&[...r.addedNodes,...r.removedNodes].some(n=>n.nodeType===1&&!n.id?.startsWith('feedcontrol-'))))schedule();}).observe(document.documentElement,{childList:true,subtree:true});
 window.addEventListener('yt-navigate-finish',schedule);window.addEventListener('popstate',schedule);
 document.addEventListener('visibilitychange',()=>{sample();lastSample=null;});window.addEventListener('pagehide',flushWatch);setInterval(sample,1000);
})();
