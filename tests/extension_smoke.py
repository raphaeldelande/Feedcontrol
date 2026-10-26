"""Vraie extension Chromium, pages YouTube simulées (aucun trafic YouTube).
Dépendance de test optionnelle : pip install playwright ; Chromium installé.
"""
import json
import tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
HTML = '''<!doctype html><html><body><ytd-browse page-subtype="home"><div id="primary"><div id="contents" style="display:flex">
<ytd-rich-item-renderer><a id="video-title" href="/watch?v=aaaaaaaaaaa">Football analyse tactique</a></ytd-rich-item-renderer>
<ytd-rich-item-renderer><a id="video-title" href="/watch?v=bbbbbbbbbbb">Bricolage tutoriel étagère</a></ytd-rich-item-renderer>
<ytd-rich-item-renderer><a id="video-title" href="/watch?v=ccccccccccc">Funny football moments compilation</a></ytd-rich-item-renderer>
</div></div></ytd-browse></body></html>'''

def run():
    with sync_playwright() as p, tempfile.TemporaryDirectory(prefix='fc-browser-') as profile:
        context = p.chromium.launch_persistent_context(profile, executable_path='/usr/lib/chromium/chromium', headless=True, ignore_default_args=['--disable-extensions'],
            args=['--no-sandbox','--enable-unsafe-extension-debugging', f'--disable-extensions-except={ROOT}', f'--load-extension={ROOT}'])
        errors = []
        context.on('page', lambda page: page.on('pageerror', lambda error: errors.append(str(error))))
        worker = context.service_workers[0] if context.service_workers else context.wait_for_event('serviceworker')
        extension_id = worker.url.split('/')[2]
        popup = context.new_page()
        popup.goto(f'chrome-extension://{extension_id}/popup.html')
        expect(popup.locator('#positive input')).to_have_count(16)
        expect(popup.locator('#bars')).to_contain_text('Aucune donnée')
        popup.locator('[data-code="bricolage"][data-key="favorites"]').check()
        popup.locator('#mode').select_option('only')
        expect(popup.locator('#saved')).to_contain_text('enregistrées')
        page = context.new_page()
        context.route('https://www.youtube.com/**', lambda route: route.fulfill(status=200, content_type='text/html', body=HTML))
        page.goto('https://www.youtube.com/')
        expect(page.locator('ytd-rich-item-renderer:not(.feedcontrol-hidden)')).to_have_count(1)
        popup.locator('#mode').select_option('favor')
        expect(page.locator('ytd-rich-item-renderer:not(.feedcontrol-hidden)')).to_have_count(3)
        popup.locator('#quality').check()
        expect(page.locator('ytd-rich-item-renderer:not(.feedcontrol-hidden)')).to_have_count(2)
        # Popup fermeture/réouverture et persistance.
        popup.reload()
        expect(popup.locator('#quality')).to_be_checked()
        expect(popup.locator('[data-code="bricolage"][data-key="favorites"]')).to_be_checked()
        popup.locator('#discovery').check()
        expect(page.locator('#feedcontrol-panel')).to_contain_text('Clé YOUTUBE_API_KEY absente', timeout=20000)
        # DOM dynamique et répétitions : les cartes originales gardent leurs liens.
        page.evaluate('''() => {const card=document.createElement('ytd-rich-item-renderer');card.innerHTML='<a id="video-title" href="/watch?v=ddddddddddd">Bricolage tutoriel table</a>';document.querySelector('#contents').append(card);}''')
        expect(page.locator('ytd-rich-item-renderer:not(.feedcontrol-hidden)')).to_have_count(3)
        expect(page.locator('a[href="/watch?v=bbbbbbbbbbb"]')).to_have_text('Bricolage tutoriel étagère')
        # Découverte contrôlée : zéro carte native compatible et vrai panneau avec fixture explicitement de test.
        context.route('http://127.0.0.1:8765/discover', lambda route: route.fulfill(status=200, content_type='application/json', body=json.dumps({'videos':[{'videoId':'eeeeeeeeeee','title':'DEMO Bricolage tutoriel','topics':['bricolage'],'category':'bricolage','flags':[],'qualityScore':.82,'qualityConfidence':.65,'evidence':['DEMO fixture'],'source':'youtube_api','channelTitle':'DEMO','limitations':'Fixture de test'}]})))
        popup.locator('#mode').select_option('only')
        page.evaluate("document.querySelector('#contents').replaceChildren()")
        expect(page.locator('#feedcontrol-panel .fc-card')).to_have_count(1)
        expect(page.locator('#feedcontrol-panel a')).to_have_attribute('href','https://www.youtube.com/watch?v=eeeeeeeeeee')
        page.locator('#feedcontrol-panel summary').click()
        page.get_by_role('button', name='Pertinente', exact=True).click()
        expect(page.get_by_role('button', name='Pertinente', exact=True)).to_have_attribute('aria-pressed','true')
        # Navigation SPA hors accueil : restauration, aucun panneau.
        page.evaluate("history.pushState({},'', '/watch?v=bbbbbbbbbbb');window.dispatchEvent(new Event('yt-navigate-finish'))")
        expect(page.locator('#feedcontrol-panel')).to_have_count(0)
        # Les écritures des événements sont conditionnées au consentement et effaçables.
        result = worker.evaluate("async()=>{await chrome.storage.local.set({tracking:false});await chrome.runtime.sendMessage({type:'FC_EVENT',kind:'watch',videoId:'x',seconds:4});return (await chrome.storage.local.get('statsV4')).statsV4}")
        assert result is None, result
        worker.evaluate("async()=>{await chrome.storage.local.set({tracking:true});await chrome.runtime.sendMessage({type:'FC_EVENT',kind:'watch',category:'bricolage',videoId:'x',seconds:4});}")
        popup.reload()
        expect(popup.locator('#totals')).to_contain_text('1 vidéos')
        popup.on('dialog', lambda dialog: dialog.accept())
        popup.locator('#reset').click()
        expect(popup.locator('#bars')).to_contain_text('Aucune donnée')
        popup.screenshot(path='/tmp/feedcontrol-popup.png', full_page=True)
        assert not errors, errors
        context.close()
        print('PASS extension MV3 : popup, persistance, filtres, DOM dynamique, découverte fixture/clé absente, feedback, SPA, consentement, statistiques, effacement ; aucune erreur JS.')

if __name__ == '__main__':
    run()
