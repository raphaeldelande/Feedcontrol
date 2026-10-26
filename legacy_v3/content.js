(()=>{
 const CARD='ytd-rich-item-renderer,ytd-video-renderer,ytd-grid-video-renderer,ytd-compact-video-renderer,ytd-reel-item-renderer,yt-lockup-view-model,ytd-rich-grid-slim-media,ytd-shorts-lockup-view-model';
 const SHELVES='ytd-rich-shelf-renderer[is-shorts],ytd-reel-shelf-renderer,ytd-shorts,ytd-guide-entry-renderer a[href="/shorts"],ytd-mini-guide-entry-renderer a[href="/shorts"]';
 const TITLE='#video-title,a#video-title-link,.yt-lockup-metadata-view-model__title,.shortsLockupViewModelHostMetadataTitle,.shortsLockupViewModelHostOutsideMetadataTitle,.shortsLockupViewModelHostMetadataTitleText,a[title][href*="/watch"],a[title][href*="/shorts/"],h3 a,h3,[aria-label][href*="/shorts/"]';
 let aiCache=new Map();let settings={...FeedControlClassifier.DEFAULTS};let scheduled=false;let pageKey='';let observed=new Set();let lastVideo='';let seconds=0;
 function send(kind,extra){try{chrome.runtime.sendMessage({type:'FC_EVENT',kind,...extra}).catch(()=>{});}catch(e){}}
 function shortCard(card){return !!(card.matches('ytd-reel-item-renderer,ytd-rich-grid-slim-media,ytd-shorts-lockup-view-model')||card.querySelector('a[href*="/shorts/"]')||card.closest('ytd-reel-shelf-renderer'))}
 function title(card){const el=card.querySelector(TITLE);const link=card.querySelector('a[href*="/shorts/"]');return (el?.getAttribute('title')||el?.getAttribute('aria-label')||el?.textContent||link?.getAttribute('title')||link?.getAttribute('aria-label')||'').trim();}
 function apply(){
  if(pageKey!==location.href){pageKey=location.href;observed=new Set();lastVideo='';}
  let visible=0,hidden=0;
  for(const card of document.querySelectorAll(CARD)){
   if(card.matches('yt-lockup-view-model')&&card.closest('ytd-rich-item-renderer,ytd-video-renderer,ytd-compact-video-renderer'))continue;
   const t=title(card);if(!t){card.classList.toggle('feedcontrol-hidden',!!(settings.enabled&&settings.shortsOff&&shortCard(card)));continue;}
   const isShort=shortCard(card);let decision=FeedControlClassifier.decide(t,settings,isShort);
   // The AI is consulted only when rules have no clear match; unknown labels stay visible until classified.
   if(decision.category==='autre' && settings.enabled && (!isShort || (!settings.shortsOff && settings.shortsFilter))){
    const ai=aiCache.get(t);
    if(ai && ai.category && ai.score>=0.42){
     const isBlocked=settings.blocked.includes(ai.category);
     const outside=settings.only.length && !settings.only.includes(ai.category);
     const active=!isShort||settings.shortsFilter;
     decision={...decision,category:ai.category,visible:!active||!(isBlocked||outside),reason:'semantic_text',score:ai.score};
    }else if(!ai || (ai.retryAfter && Date.now()>=ai.retryAfter)){
     aiCache.set(t,{pending:true});
     chrome.runtime.sendMessage({type:'FC_CLASSIFY',title:t},result=>{
      if(chrome.runtime.lastError || !result || result.error){aiCache.set(t,{retryAfter:Date.now()+30000});return;}
      aiCache.set(t,result);schedule();
     });
    }
   }
   card.classList.toggle('feedcontrol-hidden',!decision.visible);decision.visible?visible++:hidden++;
   const link=card.querySelector('a[href*="/watch"],a[href*="/shorts/"]');const id=link?.href||t;
   if(!observed.has(id)){observed.add(id);send('feed',{category:decision.category,hidden:!decision.visible});}
  }
  for(const shelf of document.querySelectorAll(SHELVES))shelf.classList.toggle('feedcontrol-hidden',!!(settings.enabled&&settings.shortsOff));
  let notice=document.getElementById('feedcontrol-notice');if(!notice){notice=document.createElement('div');notice.id='feedcontrol-notice';document.body.appendChild(notice);}
  const msg=settings.enabled?`FeedControl · ${visible} visibles · ${hidden} masquées`:'FeedControl · désactivé';if(notice.textContent!==msg)notice.textContent=msg;
 }
 function schedule(){if(scheduled)return;scheduled=true;setTimeout(()=>{scheduled=false;apply();},250);}
 chrome.storage.local.get(FeedControlClassifier.DEFAULTS).then(s=>{settings=s;schedule();});
 chrome.storage.onChanged.addListener((changes,area)=>{if(area!=='local')return;let updated=false;for(const key of Object.keys(FeedControlClassifier.DEFAULTS)){if(changes[key]){settings[key]=changes[key].newValue;updated=true;}}if(updated)schedule();});
 new MutationObserver(schedule).observe(document.documentElement,{childList:true,subtree:true});
 window.addEventListener('yt-navigate-finish',schedule);window.addEventListener('popstate',schedule);
 // Compte le temps de lecture effectif dans l'onglet visible, pas le temps passé sur la page.
 setInterval(()=>{
  if(pageKey!==location.href)schedule();
  const player=document.querySelector('video.html5-main-video,video');
  if(!player||player.paused||player.ended||document.hidden||!player.readyState)return;
  const key=location.href;if(!lastVideo||lastVideo!==key){lastVideo=key;send('view');}
  const name=document.querySelector('h1.ytd-watch-metadata,h1.ytd-reel-video-renderer,h1')?.textContent||document.title;
  const c=FeedControlClassifier.classify(name);send('watch',{category:c.category,short:location.pathname.startsWith('/shorts/'),seconds:5});
 },5000);
})();
