"""API locale FeedControl : texte explicable, modèle optionnel, découverte officielle."""
import sys
sys.dont_write_bytecode = True
import json
import os
import re
import time
import threading
import unicodedata
from pathlib import Path
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from thumbnail_analysis import ThumbnailAnalyzer

ROOT = Path(__file__).resolve().parent
# Lecture locale simple ; ne remplace jamais les variables déjà injectées.
if (ROOT / '.env').exists():
    for line in (ROOT / '.env').read_text(encoding='utf-8-sig').splitlines():
        if line.strip() and not line.lstrip().startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            os.environ.setdefault(key.strip(), value.strip().strip('\"\''))
TAX = json.loads((ROOT / 'taxonomy.json').read_text(encoding='utf-8'))
TOPICS = list(TAX)[:16]
PROFILES = json.loads((ROOT / 'genre_profiles.json').read_text(encoding='utf-8'))
RULES = json.loads((ROOT / 'classification_rules.json').read_text(encoding='utf-8'))
semantic_prompts = [(topic, 'topic', text) for topic, profile in PROFILES.items() for text in profile['positive']]
semantic_prompts += [(topic, 'negative', text) for topic, profile in PROFILES.items() for text in profile['negative']]
semantic_prompts += [(kind, 'type', ' '.join(terms)) for kind, terms, _ in RULES['types']]
semantic_prompts += [('compilation_virale', 'type', 'funny moments compilation, viral sports edit with memes, fails and humorous montage')]
api_state = {'status':'not_tested','message':'Aucune recherche effectuée depuis le démarrage.'}
MODEL_NAME = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
model = None
embeddings = None
model_lock = threading.Lock()
model_error = None
thumbnail_analyzer = ThumbnailAnalyzer()

def normalize(text):
    return re.sub('[^a-z0-9]+', ' ', ''.join(c for c in unicodedata.normalize('NFD', text.lower()) if unicodedata.category(c) != 'Mn')).strip()

def contains(text, term):
    return ' ' + normalize(term) + ' ' in ' ' + text + ' '

def load_model():
    global model, embeddings, model_error
    if os.getenv('FEEDCONTROL_SEMANTIC') != '1':
        return
    try:
        from sentence_transformers import SentenceTransformer
        loaded = SentenceTransformer(MODEL_NAME)
        references = loaded.encode([text for _, _, text in semantic_prompts], normalize_embeddings=True)
        model, embeddings = loaded, references
        model_error = None
    except Exception as exc:
        model_error = type(exc).__name__  # Ne journaliser aucune configuration d'authentification.

def classify(video):
    if isinstance(video, str):
        video = {'title': video}
    visual = thumbnail_analyzer.analyze(video.get('videoId')) if video.get('analyzeThumbnail') is True else video.get('visualAnalysis')
    ocr_text = visual.get('ocrText','') if visual and visual.get('status') == 'analyzed' else ''
    text = normalize(video.get('title', '') + ' ' + video.get('description', '') + ' ' + video.get('channelTitle', '') + ' ' + ocr_text)
    matches = [k for k, v in TAX.items() if any(contains(text, term) for term in v['terms'])]
    topics = [k for k in matches if k in TOPICS]
    flags = [k for k in matches if k not in TOPICS]
    kind, score, confidence = 'inconnu', .5, .15
    evidence = []
    if flags:
        kind = 'compilation_virale' if any(k in flags for k in ['viral', 'brainrot']) else flags[0]
        score, confidence = .15, .75
        evidence.append('Indices textuels : ' + ', '.join(flags))
    else:
        rules = RULES['types']
        for label, terms, value in rules:
            if any(contains(text, term) for term in terms):
                kind, score, confidence = label, value, .65
                evidence.append('Indices textuels de type ' + label + ' ; qualité non vérifiée.')
                break
    if any(contains(text, term) for term in RULES['motivationTerms']) and 'motivation' not in topics:
        topics.append('motivation')
    method = 'heuristic_text'
    semantic_evidence = []
    genre_signals = []
    if model is not None:
        with model_lock:
            vector = model.encode([text], normalize_embeddings=True)[0]
            scores = embeddings @ vector
        topic_scores = {t:max(float(scores[i]) for i,(label,axis,_) in enumerate(semantic_prompts) if label==t and axis=='topic') for t in TOPICS}
        topics = list(dict.fromkeys(topics + [t for t,value in topic_scores.items() if value >= .42]))
        for topic in topics:
            negative = [float(scores[i]) for i,(label,axis,_) in enumerate(semantic_prompts) if label==topic and axis=='negative']
            genre_signals.append({'topic':topic,'positiveSimilarity':round(topic_scores[topic],3),'negativeSimilarity':round(max(negative),3) if negative else None})
        negative_match = any(v['negativeSimilarity'] is not None and v['negativeSimilarity']>=.5 and v['negativeSimilarity']-v['positiveSimilarity']>=.08 for v in genre_signals)
        if negative_match and kind=='inconnu' and not flags:
            flags.append('viral');kind,score,confidence='compilation_virale',.2,.6
            evidence.append('Le texte ressemble davantage aux contre-exemples viraux du profil qu’au contenu de fond.')
        type_scores = {}
        for i,(label,axis,_) in enumerate(semantic_prompts):
            if axis == 'type':
                type_scores[label] = max(type_scores.get(label,-1),float(scores[i]))
        ranked = sorted(type_scores.items(),key=lambda item:item[1],reverse=True)
        winner, similarity = ranked[0]
        margin = similarity-ranked[1][1]
        semantic_evidence.append({'type':winner,'similarity':round(similarity,3),'margin':round(margin,3)})
        if not flags and similarity >= .48 and margin >= .06:
            if winner == 'compilation_virale':
                flags.append('viral');kind,score,confidence = winner,.2,min(.8,.55+margin)
            elif kind == 'inconnu':
                kind = winner;score = dict((k,v) for k,_,v in RULES['types'])[winner];confidence=min(.8,.55+margin)
            evidence.append('Type sémantique estimé : '+winner+' ; similarité non assimilable à une probabilité.')
        method = 'semantic_text+heuristic_quality'
    presentation_risk = 0
    if visual and visual.get('status') == 'analyzed':
        sig = visual.get('signals',{})
        if sig.get('redCircleLikeCount') or sig.get('redArrowLikeCount'):
            presentation_risk = .7
            evidence.append('Miniature analysée : formes rouges compatibles avec des cercles/flèches (indice de présentation, pas preuve de tromperie).')
        if sig.get('monochrome'):
            evidence.append('Miniature principalement monochrome : le style seul ne détermine pas le thème.')
        learned = visual.get('learned') or {}
        if learned.get('scene'):
            evidence.append('Modèle visuel : '+learned['scene'])
        if learned.get('uncertainty') == 'low':
            proposed = [t for t in learned.get('topics',[]) if t in TOPICS]
            if proposed:
                topics = list(dict.fromkeys(topics+proposed))
                evidence.append('Thèmes proposés par le modèle visuel local (hypothèse, pas une validation du contenu).')
        if learned.get('uncertainty')=='low' and learned.get('contentStyle')=='meme_montage' and kind not in ('analyse','cours','educatif','documentaire'):
            if 'viral' not in flags: flags.append('viral')
            kind,score,confidence='compilation_virale',.25,.6
            evidence.append('Le modèle visuel suggère un montage de memes ; conclusion incertaine, pas analyse de la vidéo.')
        if learned.get('montage'):
            presentation_risk = min(1,presentation_risk+.15)
        if presentation_risk >= .7 and kind == 'inconnu':
            score,confidence = .35,.55
    return {**video, 'classifierVersion':2, 'topics': topics, 'category': topics[0] if topics else 'autre', 'flags': flags,
            'contentType': kind, 'qualityScore': score, 'qualityConfidence': confidence,
            'visualAnalysis': visual, 'thumbnailAnalyzed': bool(visual and visual.get('status')=='analyzed'),
            'presentationRisk': presentation_risk, 'semanticEvidence':semantic_evidence, 'genreSignals':genre_signals,
            'evidence': evidence or ['Informations insuffisantes pour évaluer la qualité.'],
            'blockedReasons': [], 'recommendationReasons': [], 'method': method,
            'limitations': 'Vidéo non regardée ; indices textuels/visuels incertains, aucune personne identifiée.' if visual and visual.get('status')=='analyzed' else 'Miniature non analysée ; jugement limité au texte disponible.'}

class DiscoveryError(Exception):
    pass

class Discovery:
    def __init__(self, transport=None):
        self.cache = OrderedDict()
        self.lock = threading.Lock()
        self.calls = []
        self.transport = transport or self.request

    def request(self, endpoint, params):
        key = os.getenv('YOUTUBE_API_KEY')
        if not key:
            raise DiscoveryError('Clé YOUTUBE_API_KEY absente : découverte désactivée.')
        url = 'https://www.googleapis.com/youtube/v3/' + endpoint + '?' + urlencode({**params, 'key': key})
        for attempt in range(2):
            try:
                with urlopen(Request(url), timeout=8) as response:
                    return json.load(response)
            except HTTPError as exc:
                if exc.code >= 500 and attempt == 0:
                    continue
                # Ne jamais exposer l'URL contenant la clé.
                reason = 'quota épuisé ou accès refusé' if exc.code == 403 else 'requête refusée'
                raise DiscoveryError(f'YouTube API : {reason} (HTTP {exc.code}).') from None
            except (URLError, TimeoutError):
                if attempt:
                    raise DiscoveryError('YouTube API inaccessible ; réessayez plus tard.') from None
        raise DiscoveryError('YouTube API indisponible.')

    def discover(self, topics, refresh=False, small_creators=False, subscriber_threshold=50000):
        topics = tuple(dict.fromkeys(t for t in topics if t in TOPICS))[:4]
        subscriber_threshold = max(1,min(10000000,int(subscriber_threshold or 50000)))
        if not topics:
            return {'videos': [], 'message': 'Sélectionnez au moins un thème.', 'source': 'youtube_api'}
        key = (topics,small_creators)
        with self.lock:
            now = time.time()
            old = self.cache.get(key)
            if old and now-old[0] < 900 and (not refresh or now-old[0] < 45):
                result = dict(old[1]);result['cached'] = True
                result['smallCreatorCount'] = sum(v['subscriberCount'] is not None and v['subscriberCount'] < subscriber_threshold for v in result['videos'])
                result['message'] = 'Candidats en cache ; nouvelle recherche possible après 45 secondes.' if refresh else result.get('message','')
                return result
            plans = [(topic,order) for topic in topics for order in (('relevance','date') if small_creators else ('relevance',))]
            self.calls = [t for t in self.calls if now-t < 3600]
            if len(self.calls)+len(plans) > 12:
                api_state.update(status='local_limit',message='Plafond de recherches atteint.')
                raise DiscoveryError('Plafond local : 12 recherches par heure. Attendez avant de réessayer.')
            ids = []
            previous_tokens = old[1].get('pageTokens',{}) if old and refresh else {}
            tokens = {}
            try:
                for topic,order in plans:
                    token_key = topic+':'+order
                    params = {'part':'snippet','type':'video','q':PROFILES[topic]['searchQuery'],'maxResults':16,'safeSearch':'moderate','order':order,'relevanceLanguage':'fr'}
                    if previous_tokens.get(token_key):
                        params['pageToken'] = previous_tokens[token_key]
                    self.calls.append(now)
                    found = self.transport('search',params)
                    tokens[token_key] = found.get('nextPageToken')
                    ids.extend(item['id']['videoId'] for item in found.get('items',[]) if item.get('id',{}).get('videoId'))
                ids = list(dict.fromkeys(ids))[:64]
                items = []
                for offset in range(0,len(ids),50):
                    items.extend(self.transport('videos',{'part':'snippet,contentDetails,statistics','id':','.join(ids[offset:offset+50])}).get('items',[]))
                channel_ids = list(dict.fromkeys(v.get('snippet',{}).get('channelId') for v in items if v.get('snippet',{}).get('channelId')))
                channels = []
                for offset in range(0,len(channel_ids),50):
                    channels.extend(self.transport('channels',{'part':'statistics','id':','.join(channel_ids[offset:offset+50])}).get('items',[]))
                subscribers = {}
                for channel in channels:
                    stats = channel.get('statistics',{})
                    subscribers[channel['id']] = int(stats['subscriberCount']) if stats.get('hiddenSubscriberCount') is not True and 'subscriberCount' in stats else None
                videos = []
                for v in items:
                    sn = v.get('snippet',{})
                    if not sn.get('title') or not sn.get('channelId'):
                        continue
                    videos.append(classify({'videoId':v['id'],'channelId':sn['channelId'],'channelTitle':sn.get('channelTitle',''),'title':sn['title'],'description':sn.get('description',''),'thumbnail':sn.get('thumbnails',{}).get('medium',{}).get('url'),'duration':v.get('contentDetails',{}).get('duration'),'viewCount':int(v['statistics']['viewCount']) if 'viewCount' in v.get('statistics',{}) else None,'subscriberCount':subscribers.get(sn['channelId']),'source':'youtube_api'}))
            except DiscoveryError as exc:
                api_state.update(status='error',message=str(exc))
                raise
            result = {'videos':videos,'source':'youtube_api','message':'' if videos else 'Aucun résultat correspondant trouvé.','cached':False,'pageTokens':tokens,'smallCreatorSearch':small_creators,'candidateCount':len(videos),'smallCreatorCount':sum(v['subscriberCount'] is not None and v['subscriberCount'] < subscriber_threshold for v in videos),'unknownSubscriberCount':sum(v['subscriberCount'] is None for v in videos)}
            api_state.update(status='ok',message=str(len(videos))+' candidats reçus de YouTube.')
            self.cache[key] = (now,result)
            if len(self.cache)>50:
                self.cache.popitem(last=False)
            return result

discovery = Discovery()

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def allowed(self):
        origin = self.headers.get('Origin', '')
        return not origin or origin.startswith('chrome-extension://') or origin in ('http://127.0.0.1:8765', 'http://localhost:8765')

    def send_json(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        origin = self.headers.get('Origin', '')
        if self.allowed() and origin:
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Vary', 'Origin')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_json(200 if self.allowed() else 403, {})

    def do_GET(self):
        if not self.allowed():
            return self.send_json(403, {'error': 'Origine refusée'})
        if self.path != '/':
            return self.send_json(404, {'error': 'Route inconnue'})
        self.send_json(200, {'status': 'ok', 'serverVersion':'0.4.1', 'model_loaded': model is not None, 'method': 'semantic_text' if model else 'heuristic_text', 'model_error': model_error, 'discovery': bool(os.getenv('YOUTUBE_API_KEY')), 'apiState':api_state, 'vision':thumbnail_analyzer.status(), 'categories': TOPICS, 'profilesVersion':2})

    def do_POST(self):
        if not self.allowed():
            return self.send_json(403, {'error': 'Origine refusée'})
        try:
            size = int(self.headers.get('Content-Length', 0))
            if size <= 0 or size > 20000:
                return self.send_json(413, {'error': 'Corps absent ou trop volumineux'})
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError('Objet JSON requis')
            if self.path == '/classify':
                if not isinstance(data.get('title'), str) or not data['title'].strip():
                    raise ValueError('Titre requis')
                # Ne recopier aucune donnée arbitraire dans la réponse.
                video = {k: data[k] for k in ['title', 'description', 'videoId', 'channelId', 'channelTitle', 'source','analyzeThumbnail'] if k in data}
                if not isinstance(video.get('description', ''), str):
                    raise ValueError('Description invalide')
                return self.send_json(200, classify(video))
            if self.path == '/discover':
                if not isinstance(data.get('topics'), list) or not all(isinstance(t, str) for t in data['topics']):
                    raise ValueError('Liste de thèmes requise')
                return self.send_json(200, discovery.discover(data['topics'], bool(data.get('refresh')), bool(data.get('smallCreators')), data.get('subscriberThreshold',50000)))
            return self.send_json(404, {'error': 'Route inconnue'})
        except (ValueError, UnicodeDecodeError):
            self.send_json(400, {'error': 'Entrée JSON invalide'})
        except DiscoveryError as exc:
            self.send_json(503, {'error': str(exc)})
        except Exception:
            self.send_json(503, {'error': 'Service indisponible'})

def main():
    load_model()
    server = ThreadingHTTPServer(('127.0.0.1', 8765), Handler)
    print('FeedControl : http://127.0.0.1:8765 — ' + ('sémantique texte' if model else 'règles texte') + ' ; miniatures : ' + ('pixels'+(' + OCR' if thumbnail_analyzer.ocr_command else '') if thumbnail_analyzer.status()['available'] else 'indisponibles'), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == '__main__':
    main()
