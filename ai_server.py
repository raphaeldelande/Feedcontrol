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

ROOT = Path(__file__).resolve().parent
# Lecture locale simple ; ne remplace jamais les variables déjà injectées.
if (ROOT / '.env').exists():
    for line in (ROOT / '.env').read_text(encoding='utf-8-sig').splitlines():
        if line.strip() and not line.lstrip().startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            os.environ.setdefault(key.strip(), value.strip().strip('\"\''))
TAX = json.loads((ROOT / 'taxonomy.json').read_text(encoding='utf-8'))
TOPICS = list(TAX)[:16]
MODEL_NAME = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
model = None
embeddings = None
model_lock = threading.Lock()
model_error = None

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
        model = SentenceTransformer(MODEL_NAME)
        embeddings = model.encode([' '.join(TAX[t]['terms']) for t in TOPICS], normalize_embeddings=True)
    except Exception as exc:
        model_error = type(exc).__name__  # Ne journaliser aucune configuration d'authentification.

def classify(video):
    if isinstance(video, str):
        video = {'title': video}
    text = normalize(video.get('title', '') + ' ' + video.get('description', ''))
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
        rules = [('analyse', ['analyse', 'analysis', 'tactique', 'tactical', 'strategie'], .82),
                 ('cours', ['cours', 'tutorial', 'tutoriel', 'lesson', 'technique'], .82),
                 ('documentaire', ['documentaire', 'documentary'], .8),
                 ('performance_authentique', ['match integral', 'full match', 'competition', 'concert live', 'entrainement', 'training', 'workout'], .78),
                 ('educatif', ['comprendre', 'expliquer', 'science', 'reparer', 'recette', 'woodworking'], .75)]
        for label, terms, value in rules:
            if any(contains(text, term) for term in terms):
                kind, score, confidence = label, value, .65
                evidence.append('Indices textuels de type ' + label + ' ; qualité non vérifiée.')
                break
    method = 'heuristic_text'
    if model is not None:
        with model_lock:
            vector = model.encode([video['title'] + ' ' + video.get('description', '')], normalize_embeddings=True)[0]
            scores = embeddings @ vector
        semantic = [TOPICS[i] for i, s in enumerate(scores) if float(s) >= .42]
        topics = list(dict.fromkeys(topics + semantic))
        method = 'semantic_text+heuristic_quality'
    return {**video, 'topics': topics, 'category': topics[0] if topics else 'autre', 'flags': flags,
            'contentType': kind, 'qualityScore': score, 'qualityConfidence': confidence,
            'evidence': evidence or ['Informations insuffisantes pour évaluer la qualité.'],
            'blockedReasons': [], 'recommendationReasons': [], 'method': method,
            'limitations': 'Texte seulement ; miniature et vidéo non analysées. Qualité estimée par indices textuels.'}

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

    def discover(self, topics, refresh=False):
        topics = tuple(dict.fromkeys(t for t in topics if t in TOPICS))[:4]
        if not topics:
            return {'videos': [], 'message': 'Sélectionnez au moins un thème.', 'source': 'youtube_api'}
        with self.lock:  # Une seule recherche à la fois, également pour les appels identiques concurrents.
            now = time.time()
            cached = self.cache.get(topics)
            if cached and now - cached[0] < 900:
                return {**cached[1], 'cached': True}
            self.calls = [t for t in self.calls if now - t < 3600]
            if len(self.calls) + len(topics) > 12:
                raise DiscoveryError('Plafond local : 12 recherches par heure. Attendez avant de réessayer.')
            ids = []
            for topic in topics:
                self.calls.append(now)
                result = self.transport('search', {'part': 'snippet', 'type': 'video', 'q': TAX[topic]['label'], 'maxResults': 8, 'safeSearch': 'moderate'})
                ids.extend(item['id']['videoId'] for item in result.get('items', []) if item.get('id', {}).get('videoId'))
            ids = list(dict.fromkeys(ids))[:32]
            videos = []
            if ids:
                details = self.transport('videos', {'part': 'snippet,contentDetails,statistics', 'id': ','.join(ids)})
                channel_ids = list(dict.fromkeys(v['snippet']['channelId'] for v in details.get('items', [])))
                channels = self.transport('channels', {'part': 'statistics', 'id': ','.join(channel_ids)}) if channel_ids else {'items': []}
                subscribers = {c['id']: None if c.get('statistics', {}).get('hiddenSubscriberCount', True) else int(c['statistics']['subscriberCount']) if 'subscriberCount' in c.get('statistics', {}) else None for c in channels.get('items', [])}
                for v in details.get('items', []):
                    sn = v['snippet']
                    thumb = sn.get('thumbnails', {}).get('medium', {}).get('url')
                    videos.append(classify({'videoId': v['id'], 'channelId': sn['channelId'], 'channelTitle': sn.get('channelTitle', ''), 'title': sn['title'], 'description': sn.get('description', ''), 'thumbnail': thumb, 'thumbnailAnalyzed': False, 'duration': v.get('contentDetails', {}).get('duration'), 'viewCount': int(v['statistics']['viewCount']) if 'viewCount' in v.get('statistics', {}) else None, 'subscriberCount': subscribers.get(sn['channelId']), 'source': 'youtube_api'}))
            result = {'videos': videos, 'source': 'youtube_api', 'message': '' if videos else 'Aucun résultat correspondant trouvé.', 'cached': False}
            self.cache[topics] = (now, result)
            if len(self.cache) > 50:
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
        self.send_json(200, {'status': 'ok', 'model_loaded': model is not None, 'method': 'semantic_text' if model else 'heuristic_text', 'model_error': model_error, 'discovery': bool(os.getenv('YOUTUBE_API_KEY')), 'categories': TOPICS})

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
                video = {k: data[k] for k in ['title', 'description', 'videoId', 'channelId', 'source'] if k in data}
                if not isinstance(video.get('description', ''), str):
                    raise ValueError('Description invalide')
                return self.send_json(200, classify(video))
            if self.path == '/discover':
                if not isinstance(data.get('topics'), list) or not all(isinstance(t, str) for t in data['topics']):
                    raise ValueError('Liste de thèmes requise')
                return self.send_json(200, discovery.discover(data['topics'], bool(data.get('refresh'))))
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
    print('FeedControl : http://127.0.0.1:8765 — ' + ('sémantique' if model else 'heuristique texte (sans vision)'), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == '__main__':
    main()
