"""Local title classification API. Run with the parent .venv Python."""
import sys

# Keep Python bytecode out of the unpacked Chrome extension.
sys.dont_write_bytecode = True

import json
import math
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
LABELS = {
    "brainrot": ["absurd internet meme compilation skibidi toilet italian brainrot", "fast streamer meme edit with subway surfers gameplay"],
    "suggestif": ["sexually suggestive thirst trap dance clickbait"],
    "culture": ["history geography philosophy literature educational documentary"],
    "science": ["science artificial intelligence mathematics and programming tutorial"],
    "motivation": ["discipline motivation productivity studying self improvement"],
    "sport": ["sports training football rugby basketball highlights"],
}
model = None
reference_embeddings = None
prompts = [(category, text) for category, texts in LABELS.items() for text in texts]
model_lock = threading.Lock()


def load_model():
    """Load once, including reference embeddings, before accepting requests."""
    global model, reference_embeddings
    with model_lock:
        if model is None:
            from sentence_transformers import SentenceTransformer
            loaded = SentenceTransformer(MODEL_NAME)
            references = loaded.encode([text for _, text in prompts], convert_to_tensor=True)
            reference_embeddings = references
            model = loaded


def classify(title):
    from sentence_transformers import util
    load_model()
    with model_lock:
        embedding = model.encode(title, convert_to_tensor=True)
        values = util.cos_sim(embedding, reference_embeddings)[0].tolist()
    if not all(math.isfinite(value) for value in values):
        raise RuntimeError("Model returned non-finite scores")
    scores = {
        category: round(max(values[i] for i, (label, _) in enumerate(prompts) if label == category), 3)
        for category in LABELS
    }
    category = max(scores, key=scores.get)
    return {"category": category, "score": scores[category], "scores": scores, "method": "semantic_text"}


class Handler(BaseHTTPRequestHandler):
    # self.headers belongs to BaseHTTPRequestHandler: never override it.
    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if self.path != "/":
            self.send_json(404, {"error": "Unknown route"})
            return
        self.send_json(200, {"status": "ok", "model": MODEL_NAME, "model_loaded": model is not None, "categories": list(LABELS)})

    def do_POST(self):
        if self.path != "/classify":
            self.send_json(404, {"error": "Unknown route"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size <= 0:
                raise ValueError("Missing request body")
            if size > 10000:
                self.send_json(413, {"error": "Payload too large"})
                return
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError("Expected a JSON object")
            title = data.get("title")
            if not isinstance(title, str) or not title.strip():
                raise ValueError("Missing title")
        except (ValueError, UnicodeDecodeError) as error:
            self.send_json(400, {"error": str(error)})
            return
        try:
            self.send_json(200, classify(title.strip()[:400]))
        except Exception:
            self.log_error("Semantic classification failed")
            self.send_json(503, {"error": "Semantic model unavailable"})


def main():
    print("Loading FeedControl semantic model (first run may download files)...", flush=True)
    load_model()
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    print("FeedControl AI ready at http://127.0.0.1:8765 (model loaded)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
