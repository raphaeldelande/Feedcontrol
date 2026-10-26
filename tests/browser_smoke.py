"""Intégration DOM réelle Chromium, API chrome simulées. PAS un test d'extension chargée."""
import json
import tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
ROOT = Path(__file__).resolve().parents[1]
SHIM = r'''(() => {
 const listeners=[];
 const emit=(changes)=>listeners.forEach(fn=>fn(changes,'local'));
 window.addEventListener('storage', e=>{if(e.key==='fc-test-store'){const old=JSON.parse(e.oldValue||'{}'),next=JSON.parse(e.newValue||'{}');const changes={};for(const key of new Set([...Object.keys(old),...Object.keys(next)]))if(JSON.stringify(old[key])!==JSON.stringify(next[key]))changes[key]={oldValue:old[key],newValue:next[key]};emit(changes);}});
 const getStore=()=>JSON.parse(localStorage.getItem('fc-test-store')||'{}');
 const storage={get:async keys=>{const all=getStore();if(keys===null)return all;if(typeof keys==='string')return {[keys]:all[keys]};return Object.fromEntries((Array.isArray(keys)?keys:Object.keys(keys)).map(k=>[k,all[k]??keys[k]]));},set:async patch=>{const old=getStore();localStorage.setItem('fc-test-store',JSON.stringify({...old,...patch}));emit(Object.fromEntries(Object.entries(patch).map(([k,v])=>[k,{oldValue:old[k],newValue:v}])));},remove:async keys=>{const all=getStore(),changes={};for(const k of Array.isArray(keys)?keys:[keys]){changes[k]={oldValue:all[k]};delete all[k];}localStorage.setItem('fc-test-store',JSON.stringify(all));emit(changes);}};
 window.chrome={storage:{local:storage,onChanged:{addListener:fn=>listeners.push(fn)}},tabs:{create:async()=>{}},runtime:{getURL:path=>'/__fc__/'+path,sendMessage:async m=>{
  if(m.type==='FC_STATUS')return {status:'offline',error:'DEMO serveur arrêté'};
  if(m.type==='FC_CLASSIFY')return {...FeedControlClassifier.classify(m.video),degraded:true};
  if(m.type==='FC_DISCOVER'){(window.__discoveryCalls??=[]).push(m);if(!getStore().testAPI)return {error:'DEMO Clé YOUTUBE_API_KEY absente'};if(m.topics.includes('cuisine'))return {videos:[{...FeedControlClassifier.classify('DEMO cuisine recette pas à pas'),videoId:'fffffffffff',subscriberCount:3200,duration:'PT8M',channelTitle:'DEMO petite chaîne',source:'youtube_api'},{...FeedControlClassifier.classify('DEMO cuisine recette pas à pas'),videoId:'ggggggggggg',subscriberCount:2000000,duration:'PT8M',channelTitle:'DEMO grande chaîne',source:'youtube_api'}]};return {videos:[{...FeedControlClassifier.classify('Bricolage tutoriel DEMO'),videoId:'eeeeeeeeeee',channelTitle:'DEMO fixture',source:'youtube_api'}]};}
  if(m.type==='FC_FEEDBACK'){const all=getStore();await storage.set({feedback:{...all.feedback,[m.videoId]:{verdict:m.verdict}}});return {ok:true};}
  if(m.type==='FC_CLEAR'){await storage.remove('statsV4');return {ok:true};}
  return {ok:true};
 }}};
})();'''
HTML='''<!doctype html><html><head><meta charset="utf-8"></head><body><ytd-browse page-subtype="home"><div id="primary"><div id="contents" style="display:flex"><ytd-rich-item-renderer><a id="video-title" href="/watch?v=aaaaaaaaaaa">Football analyse tactique</a></ytd-rich-item-renderer><ytd-rich-item-renderer><a id="video-title" href="/watch?v=bbbbbbbbbbb">Bricolage tutoriel étagère</a></ytd-rich-item-renderer><ytd-rich-item-renderer><a id="video-title" href="/watch?v=ccccccccccc">Funny football moments compilation</a></ytd-rich-item-renderer></div></div></ytd-browse><script src="/__fc__/taxonomy.js"></script><script src="/__fc__/classification_rules.js"></script><script src="/__fc__/classifier.js"></script><script src="/__fc__/content.js"></script></body></html>'''
def run():
 with sync_playwright() as p,tempfile.TemporaryDirectory() as profile:
  context=p.chromium.launch_persistent_context(profile,executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  context.add_init_script(SHIM)
  def route(req):
   path=req.request.url.split('youtube.com',1)[1]
   if path.startswith('/__fc__/'):
    f=ROOT/path[len('/__fc__/'):]
    req.fulfill(status=200,body=f.read_bytes(),content_type='text/html' if f.suffix=='.html' else 'text/css' if f.suffix=='.css' else 'application/javascript')
   else:req.fulfill(status=200,body=HTML,content_type='text/html')
  context.route('https://www.youtube.com/**',route)
  errors=[]
  context.on('page',lambda page:page.on('pageerror',lambda e:errors.append(str(e))))
  popup=context.new_page();popup.goto('https://www.youtube.com/__fc__/popup.html')
  expect(popup.locator('#positive input')).to_have_count(16)
  expect(popup.locator('#bars')).to_contain_text('Aucune donnée')
  popup.locator('[data-code="bricolage"][data-key="favorites"]').check();popup.locator('#mode').select_option('only')
  page=context.new_page();page.goto('https://www.youtube.com/')
  expect(page.locator('ytd-rich-item-renderer:not(.feedcontrol-hidden)')).to_have_count(1)
  popup.locator('#mode').select_option('favor')
  expect(page.locator('ytd-rich-item-renderer:not(.feedcontrol-hidden)')).to_have_count(3)
  popup.locator('#quality').check()
  expect(page.locator('ytd-rich-item-renderer:not(.feedcontrol-hidden)')).to_have_count(2)
  popup.reload();expect(popup.locator('#quality')).to_be_checked()
  expect(popup.locator('[data-code="bricolage"][data-key="favorites"]')).to_be_checked()
  popup.locator('#discovery').check()
  expect(page.locator('#feedcontrol-panel')).to_contain_text('Clé YOUTUBE_API_KEY absente')
  page.evaluate('''()=>{const card=document.createElement('ytd-rich-item-renderer');card.innerHTML='<a id="video-title" href="/watch?v=ddddddddddd">Bricolage tutoriel table</a>';document.querySelector('#contents').append(card);}''')
  expect(page.locator('ytd-rich-item-renderer:not(.feedcontrol-hidden)')).to_have_count(3)
  page.evaluate("chrome.storage.local.set({testAPI:true})")
  popup.locator('#mode').select_option('only');page.evaluate("document.querySelector('#contents').replaceChildren()")
  expect(page.locator('#feedcontrol-panel .fc-card')).to_have_count(1)
  expect(page.locator('#feedcontrol-panel a')).to_have_attribute('href','https://www.youtube.com/watch?v=eeeeeeeeeee')
  page.locator('#feedcontrol-panel summary').click();page.get_by_role('button',name='Pertinente',exact=True).click()
  expect(page.get_by_role('button',name='Pertinente',exact=True)).to_have_attribute('aria-pressed','true')
  # Régressions : une seule colonne, y compris en fenêtre étroite ; aucune carte tronquée.
  for width in [280,320,400]:
   popup.set_viewport_size({'width':width,'height':700})
   assert popup.evaluate('document.documentElement.scrollWidth')<=width
   rects=popup.locator('#positive .category').evaluate_all('(els)=>els.map(e=>({x:e.getBoundingClientRect().x,right:e.getBoundingClientRect().right,y:e.getBoundingClientRect().y}))')
   assert all(r['x']>=0 and r['right']<=width for r in rects)
   assert len({round(r['x']) for r in rects})==1
  # Mode Uniquement déclenche de nouvelles vidéos Cuisine sans activer manuellement Découvertes.
  popup.locator('[data-code="bricolage"][data-key="favorites"]').uncheck()
  popup.locator('[data-code="cuisine"][data-key="favorites"]').check()
  popup.locator('#discovery').uncheck()
  expect(page.locator('#feedcontrol-panel .fc-card')).to_have_count(2)
  expect(page.locator('#feedcontrol-panel')).to_contain_text('DEMO cuisine recette')
  assert page.evaluate('window.__discoveryCalls.at(-1).topics.includes("cuisine")')
  popup.locator('#smallCreators').check()
  expect(page.locator('#feedcontrol-panel')).to_contain_text('candidats compatibles sous')
  expect(page.locator('#feedcontrol-panel .fc-card').first).to_contain_text('DEMO petite chaîne')
  page.wait_for_function('window.__discoveryCalls?.at(-1)?.smallCreators === true')
  # Shorts modernes sans titre et Shorts de sport sans pédagogie ne passent pas silencieusement.
  popup.locator('#mode').select_option('favor')
  page.evaluate('''()=>{const root=document.querySelector('#contents');root.innerHTML='<ytm-shorts-lockup-view-model><a href="/shorts/hhhhhhhhhhh"></a></ytm-shorts-lockup-view-model><ytd-reel-item-renderer><a aria-label="Football insane highlights" href="/shorts/iiiiiiiiiii"></a></ytd-reel-item-renderer>';}''')
  expect(page.locator('ytm-shorts-lockup-view-model.feedcontrol-hidden')).to_have_count(1)
  expect(page.locator('ytd-reel-item-renderer.feedcontrol-hidden')).to_have_count(1)
  page.evaluate("history.pushState({},'','/watch?v=bbbbbbbbbbb');window.dispatchEvent(new Event('yt-navigate-finish'))")
  expect(page.locator('#feedcontrol-panel')).to_have_count(0)
  popup.evaluate("chrome.storage.local.set({statsV4:{days:{[new Date().toISOString().slice(0,10)]:{seconds:60,views:1,hidden:0,shortsSeconds:0,categories:{bricolage:{seconds:60,views:1}}}}}})")
  expect(popup.locator('#totals')).to_contain_text('1 vidéos')
  popup.on('dialog',lambda d:d.accept());popup.locator('#reset').click();expect(popup.locator('#bars')).to_contain_text('Aucune donnée')
  # Contrôle géométrique de l'UI et capture des trois panneaux.
  assert popup.evaluate('document.body.scrollWidth')<=400
  popup.screenshot(path='/tmp/feedcontrol-popup.png',full_page=True)
  assert not errors,errors
  context.close()
  print('PASS Chromium DOM : popup, préférences, filtres, découverte DEMO/échec, feedback, SPA, statistiques/effacement. APIs Chrome SIMULÉES ; aucune erreur JS.')
if __name__=='__main__':run()
