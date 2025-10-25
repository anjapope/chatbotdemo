#!/usr/bin/env python3
"""Minimal mock backend using only Python stdlib.
Handles OPTIONS /chat and POST /chat and returns a simple JSON reply.
"""
import json
import os
import ssl
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler

# Load simple .env file into environment (no external deps). This lets you keep
# secrets out of the chat and version control. Create a `.env` file in the
# project root with lines like: OPENAI_API_KEY=sk-....
if os.path.exists('.env'):
    try:
        with open('.env', 'r', encoding='utf-8') as _env:
            for raw in _env:
                line = raw.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                k = k.strip()
                v = v.strip()
                # only set if not already in environment
                os.environ.setdefault(k, v)
    except Exception:
        pass

# Optional reranker trained from reviews.json (import after .env so RERANK_N can come from .env)
try:
    from reranker import train_from_reviews, score_text
    RERANKER_SCORES = train_from_reviews('reviews.json')
except Exception:
    RERANKER_SCORES = {}

# How many candidates to request from OpenAI for reranking. Set RERANK_N=1 to disable reranking.
# Default increased to 5 to request more candidates (higher chance of better rerank at cost of latency/cost).
try:
    RERANK_N = int(os.environ.get('RERANK_N', '5'))
except Exception:
    RERANK_N = 5

class Handler(BaseHTTPRequestHandler):
    def _set_cors_headers(self, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        # Allow the admin token header used by the admin UI
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Admin-Token')
        self.end_headers()

    def do_OPTIONS(self):
        # Used by the frontend to 'ping' the backend
        self._set_cors_headers(200)

    def do_GET(self):
        # Serve a preloaded peer review dataset for classroom mock exercises
        if self.path == '/peer_dataset':
            try:
                with open('peer_dataset.json', 'r', encoding='utf-8') as f:
                    dataset = json.load(f)
            except Exception:
                dataset = []
            # Also include any authenticated reviews from reviews.json so admin-approved reviews
            # surface in the peer review exercises. Map reviews into the same item shape.
            try:
                with open('reviews.json', 'r', encoding='utf-8') as rf:
                    reviews = json.load(rf)
            except Exception:
                reviews = []
            if isinstance(reviews, list):
                for r in reviews:
                    try:
                        # Include any review entries (no admin authentication required)
                        if isinstance(r, dict):
                            # Create a lightweight dataset item from the review
                            item_id = r.get('messageId') or ('review-' + (r.get('timestamp') or ''))
                            # Use the review comment or messageId as the question placeholder
                            question = r.get('comment') or item_id
                            assistant_text = r.get('assistantText') or ''
                            rating = r.get('rating') if 'rating' in r else None
                            review_entry = {'author': r.get('authenticatedBy') or r.get('author') or 'user', 'rating': rating, 'comment': r.get('comment','')}
                            mapped = {
                                'id': item_id,
                                'question': question,
                                'assistantResponses': [
                                    {
                                        'text': assistant_text,
                                        'reviews': [ review_entry ]
                                    }
                                ]
                            }
                            dataset.append(mapped)
                    except Exception:
                        # ignore malformed review entries
                        pass
            self._set_cors_headers(200)
            self.wfile.write(json.dumps(dataset).encode('utf-8'))
            return
        if self.path == '/peer_rank_summary':
            # Return aggregated vote counts from peer_rankings.json in shape { itemId: { '0': count, '1': count } }
            try:
                with open('peer_rankings.json', 'r', encoding='utf-8') as f:
                    ranks = json.load(f)
            except Exception:
                ranks = []
            summary = {}
            if isinstance(ranks, list):
                for r in ranks:
                    try:
                        item = r.get('itemId')
                        idx = r.get('responseIndex')
                        if item is None or idx is None:
                            continue
                        idx = str(int(idx))
                        if item not in summary:
                            summary[item] = {'0': 0, '1': 0}
                        if idx not in summary[item]:
                            summary[item][idx] = 0
                        summary[item][idx] += 1
                    except Exception:
                        pass
            self._set_cors_headers(200)
            self.wfile.write(json.dumps(summary).encode('utf-8'))
            return
        if self.path == '/reviews':
            try:
                with open('reviews.json', 'r', encoding='utf-8') as f:
                    reviews = json.load(f)
            except Exception:
                reviews = []
            self._set_cors_headers(200)
            self.wfile.write(json.dumps(reviews).encode('utf-8'))
            return

        # Admin-only listing endpoint
        if self.path == '/admin/reviews':
            token = self.headers.get('X-Admin-Token')
            ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN', 'secret-token')
            if token != ADMIN_TOKEN:
                self._set_cors_headers(403)
                self.wfile.write(json.dumps({'error': 'forbidden'}).encode('utf-8'))
                return
            try:
                with open('reviews.json', 'r', encoding='utf-8') as f:
                    reviews = json.load(f)
            except Exception:
                reviews = []
            self._set_cors_headers(200)
            self.wfile.write(json.dumps(reviews).encode('utf-8'))
            return

        # Admin endpoint to fetch peer rankings
        if self.path == '/admin/peer_rankings':
            token = self.headers.get('X-Admin-Token')
            ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN', 'secret-token')
            if token != ADMIN_TOKEN:
                self._set_cors_headers(403)
                self.wfile.write(json.dumps({'error': 'forbidden'}).encode('utf-8'))
                return
            try:
                with open('peer_rankings.json', 'r', encoding='utf-8') as f:
                    ranks = json.load(f)
            except Exception:
                ranks = []
            self._set_cors_headers(200)
            self.wfile.write(json.dumps(ranks).encode('utf-8'))
            return

    def do_POST(self):
        global RERANKER_SCORES
        if self.path == '/review':
            # Save or update review in reviews.json (deduplicate by messageId)
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length else b''
            try:
                review = json.loads(body.decode('utf-8') or '{}')
            except Exception:
                self._set_cors_headers(400)
                self.wfile.write(json.dumps({'error': 'Invalid JSON'}).encode())
                return

            if not isinstance(review, dict) or 'messageId' not in review:
                self._set_cors_headers(400)
                self.wfile.write(json.dumps({'error': 'Missing messageId'}).encode())
                return

            # Load existing reviews
            try:
                with open('reviews.json', 'r', encoding='utf-8') as f:
                    reviews = json.load(f)
            except Exception:
                reviews = []

            # Check for existing review with same messageId
            existing_index = None
            for i, r in enumerate(reviews):
                if isinstance(r, dict) and r.get('messageId') == review.get('messageId'):
                    existing_index = i
                    break

            if existing_index is not None:
                # Update existing review (overwrite)
                reviews[existing_index] = review
                status_code = 200
                result = {'status': 'updated'}
            else:
                reviews.append(review)
                status_code = 201
                result = {'status': 'created'}

            try:
                with open('reviews.json', 'w', encoding='utf-8') as f:
                    json.dump(reviews, f, indent=2)
            except Exception as e:
                self._set_cors_headers(500)
                self.wfile.write(json.dumps({'error': 'Failed to save review', 'detail': str(e)}).encode())
                return
            # Reload reranker scores so new reviews affect ranking immediately
            try:
                # update module-level RERANKER_SCORES if reranker module is available
                if 'train_from_reviews' in globals():
                    try:
                        RERANKER_SCORES = train_from_reviews('reviews.json')
                    except Exception:
                        pass
            except Exception:
                pass

            self._set_cors_headers(status_code)
            self.wfile.write(json.dumps(result).encode())
            return

        if self.path == '/suggestion':
            # Save suggestion into suggestions.json
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length else b''
            try:
                suggestion = json.loads(body.decode('utf-8') or '{}')
            except Exception:
                self._set_cors_headers(400)
                self.wfile.write(json.dumps({'error': 'Invalid JSON'}).encode())
                return
            # Minimal validation
            if not isinstance(suggestion, dict) or 'messageId' not in suggestion or 'suggestedText' not in suggestion:
                self._set_cors_headers(400)
                self.wfile.write(json.dumps({'error': 'Missing fields'}).encode())
                return
            try:
                with open('suggestions.json', 'r', encoding='utf-8') as f:
                    suggestions = json.load(f)
            except Exception:
                suggestions = []
            suggestions.append(suggestion)
            try:
                with open('suggestions.json', 'w', encoding='utf-8') as f:
                    json.dump(suggestions, f, indent=2)
            except Exception as e:
                self._set_cors_headers(500)
                self.wfile.write(json.dumps({'error': 'Failed to save suggestion', 'detail': str(e)}).encode())
                return
            self._set_cors_headers(201)
            self.wfile.write(json.dumps({'status': 'created'}).encode())
            return

        # Receive a student's ranking for a peer review (mock classroom)
        if self.path == '/peer/rank':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length else b''
            try:
                payload = json.loads(body.decode('utf-8') or '{}')
            except Exception:
                self._set_cors_headers(400)
                self.wfile.write(json.dumps({'error': 'Invalid JSON'}).encode())
                return
            # minimal validation
            if not isinstance(payload, dict) or 'itemId' not in payload or 'responseIndex' not in payload:
                self._set_cors_headers(400)
                self.wfile.write(json.dumps({'error': 'Missing fields'}).encode())
                return
            try:
                with open('peer_rankings.json', 'r', encoding='utf-8') as f:
                    ranks = json.load(f)
            except Exception:
                ranks = []
            ranks.append(payload)
            try:
                with open('peer_rankings.json', 'w', encoding='utf-8') as f:
                    json.dump(ranks, f, indent=2)
            except Exception as e:
                self._set_cors_headers(500)
                self.wfile.write(json.dumps({'error': 'Failed to save ranking', 'detail': str(e)}).encode())
                return
            self._set_cors_headers(201)
            self.wfile.write(json.dumps({'status': 'created'}).encode())
            return

        # Admin-only delete endpoint
        if self.path == '/admin/review/delete':
            token = self.headers.get('X-Admin-Token')
            ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN', 'secret-token')
            if token != ADMIN_TOKEN:
                self._set_cors_headers(403)
                self.wfile.write(json.dumps({'error': 'forbidden'}).encode('utf-8'))
                return
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length else b''
            try:
                payload = json.loads(body.decode('utf-8') or '{}')
            except Exception:
                self._set_cors_headers(400)
                self.wfile.write(json.dumps({'error': 'Invalid JSON'}).encode())
                return
            messageId = payload.get('messageId')
            if not messageId:
                self._set_cors_headers(400)
                self.wfile.write(json.dumps({'error': 'Missing messageId'}).encode())
                return
            try:
                with open('reviews.json', 'r', encoding='utf-8') as f:
                    reviews = json.load(f)
            except Exception:
                reviews = []
            new_reviews = [r for r in reviews if not (isinstance(r, dict) and r.get('messageId') == messageId)]
            try:
                with open('reviews.json', 'w', encoding='utf-8') as f:
                    json.dump(new_reviews, f, indent=2)
            except Exception as e:
                self._set_cors_headers(500)
                self.wfile.write(json.dumps({'error': 'Failed to delete review', 'detail': str(e)}).encode())
                return
            # Reload reranker after deletion
            try:
                if 'train_from_reviews' in globals():
                    try:
                        RERANKER_SCORES = train_from_reviews('reviews.json')
                    except Exception:
                        pass
            except Exception:
                pass
            self._set_cors_headers(200)
            self.wfile.write(json.dumps({'status': 'deleted'}).encode())
            return

        # Admin-only endpoint to authenticate (approve) a review so it can be used in peer datasets
        if self.path == '/admin/review/authenticate':
            token = self.headers.get('X-Admin-Token')
            ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN', 'secret-token')
            if token != ADMIN_TOKEN:
                self._set_cors_headers(403)
                self.wfile.write(json.dumps({'error': 'forbidden'}).encode('utf-8'))
                return
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length else b''
            try:
                payload = json.loads(body.decode('utf-8') or '{}')
            except Exception:
                self._set_cors_headers(400)
                self.wfile.write(json.dumps({'error': 'Invalid JSON'}).encode())
                return
            messageId = payload.get('messageId')
            if not messageId:
                self._set_cors_headers(400)
                self.wfile.write(json.dumps({'error': 'Missing messageId'}).encode())
                return
            try:
                with open('reviews.json', 'r', encoding='utf-8') as f:
                    reviews = json.load(f)
            except Exception:
                reviews = []
            found = False
            for r in reviews:
                if isinstance(r, dict) and r.get('messageId') == messageId:
                    r['authenticated'] = True
                    r['authenticatedBy'] = payload.get('adminName') or 'admin'
                    r['authenticatedAt'] = payload.get('timestamp') or ("%s" % (__import__('datetime').datetime.utcnow().isoformat() + 'Z'))
                    found = True
                    break
            if not found:
                self._set_cors_headers(404)
                self.wfile.write(json.dumps({'error': 'review not found'}).encode())
                return
            try:
                with open('reviews.json', 'w', encoding='utf-8') as f:
                    json.dump(reviews, f, indent=2)
            except Exception as e:
                self._set_cors_headers(500)
                self.wfile.write(json.dumps({'error': 'Failed to save review', 'detail': str(e)}).encode())
                return
            # Reload reranker after authentication (so authenticated reviews can be used if desired)
            try:
                if 'train_from_reviews' in globals():
                    try:
                        RERANKER_SCORES = train_from_reviews('reviews.json')
                    except Exception:
                        pass
            except Exception:
                pass
            self._set_cors_headers(200)
            self.wfile.write(json.dumps({'status': 'authenticated'}).encode())
            return

        if self.path != '/chat':
            self._set_cors_headers(404)
            self.wfile.write(json.dumps({'error': 'Not found'}).encode())
            return

        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length else b''
        try:
            data = json.loads(body.decode('utf-8') or '{}')
        except Exception:
            self._set_cors_headers(400)
            self.wfile.write(json.dumps({'error': 'Invalid JSON'}).encode())
            return

        messages = data.get('messages', []) if isinstance(data, dict) else []
        # If an OpenAI API key is present, proxy the request to OpenAI's Chat Completions API
        OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
        if OPENAI_API_KEY:
            # Prefer model from client, otherwise env default
            model = None
            if isinstance(data, dict) and data.get('model'):
                model = data.get('model')
            if not model:
                model = os.environ.get('OPENAI_MODEL', 'gpt-3.5-turbo')

            # Request multiple candidates so we can rerank using collected reviews
            n = RERANK_N if RERANKER_SCORES else 1
            # If user explicitly requested a single sample, respect it
            if isinstance(data, dict) and data.get('n'):
                try:
                    n = int(data.get('n'))
                except Exception:
                    pass
            payload = {'model': model, 'messages': messages, 'n': max(1, n)}
            # Allow the client to suggest temperature (optional)
            if isinstance(data, dict) and 'temperature' in data:
                try:
                    payload['temperature'] = float(data.get('temperature'))
                except Exception:
                    pass
            # Allow client max tokens
            if isinstance(data, dict) and 'max_tokens' in data:
                try:
                    payload['max_tokens'] = int(data.get('max_tokens'))
                except Exception:
                    pass
            

            body_bytes = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                'https://api.openai.com/v1/chat/completions',
                data=body_bytes,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {OPENAI_API_KEY}'
                },
                method='POST'
            )
            try:
                ctx = ssl.create_default_context()
                with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
                    raw = resp.read().decode('utf-8')
                    try:
                        parsed = json.loads(raw)
                    except Exception:
                        parsed = None

                # Extract choices and optionally rerank them using token scores
                assistant_text = None
                best_score = -1.0
                replies = []
                best_index = None
                # Determine weights for composite scoring: prefer request-provided weights, then env vars, else equal
                weights = None
                if isinstance(data, dict) and isinstance(data.get('weights'), dict):
                    weights = data.get('weights')
                else:
                    try:
                        weights = {
                            'factuality': float(os.environ.get('OPENAI_WEIGHT_FACTUALITY', '0') or 0),
                            'clarity': float(os.environ.get('OPENAI_WEIGHT_CLARITY', '0') or 0),
                            'ethics': float(os.environ.get('OPENAI_WEIGHT_ETHICS', '0') or 0),
                        }
                    except Exception:
                        weights = None

                if parsed and isinstance(parsed, dict):
                    choices = parsed.get('choices')
                    if isinstance(choices, list) and len(choices) > 0:
                        # Collect all returned candidate texts so the frontend can show A/B (or more)
                        for c in choices:
                            # extract text from either new or older style
                            text = None
                            msg = c.get('message') if isinstance(c, dict) else None
                            if isinstance(msg, dict) and 'content' in msg:
                                text = msg.get('content')
                            if text is None and isinstance(c, dict) and 'text' in c:
                                text = c.get('text')
                            if text is None:
                                continue
                            replies.append(text)
                            if RERANKER_SCORES:
                                try:
                                    score = score_text(text, RERANKER_SCORES, weights=weights)
                                except Exception:
                                    try:
                                        score = score_text(text, RERANKER_SCORES)
                                    except Exception:
                                        score = 0.0
                            else:
                                score = 0.5
                            if score > best_score:
                                best_score = score
                                assistant_text = text
                                # index within the replies array
                                best_index = len(replies) - 1

                if assistant_text is None:
                    # Fallback to echoing the last user message
                    last_user = None
                    for m in reversed(messages):
                        if isinstance(m, dict) and m.get('role') == 'user':
                            last_user = m.get('content')
                            break
                    assistant_text = f"Mock fallback reply — you said: {last_user or '(no user message)'}"

                # Ensure we have a replies array for the frontend; if none were returned, include the chosen assistant_text
                if not replies:
                    replies = [assistant_text]
                    best_index = 0 if best_index is None else best_index

                self._set_cors_headers(200)
                self.wfile.write(json.dumps({'reply': assistant_text, 'score': best_score, 'replies': replies, 'best_index': best_index}).encode('utf-8'))
                return
            except urllib.error.HTTPError as e:
                try:
                    detail = e.read().decode('utf-8')
                except Exception:
                    detail = str(e)
                self._set_cors_headers(502)
                self.wfile.write(json.dumps({'error': 'OpenAI error', 'detail': detail}).encode('utf-8'))
                return
            except Exception as e:
                self._set_cors_headers(502)
                self.wfile.write(json.dumps({'error': 'OpenAI request failed', 'detail': str(e)}).encode('utf-8'))
                return

        # Fallback behavior when OPENAI_API_KEY is not set: simple mock replies
        last_user = None
        for m in reversed(messages):
            if isinstance(m, dict) and m.get('role') == 'user':
                last_user = m.get('content')
                break

        # Respect an 'n' parameter from the client so Compare can request multiple candidates
        n = 1
        if isinstance(data, dict) and 'n' in data:
            try:
                n = int(data.get('n') or 1)
            except Exception:
                n = 1

        replies = []
        for i in range(max(1, n)):
            if n == 1:
                text = f"Mock reply — you said: {last_user or '(no user message)'}"
            else:
                text = f"Mock reply #{i+1} — you said: {last_user or '(no user message)'}"
            replies.append(text)

        self._set_cors_headers(200)
        response = {'reply': replies[0], 'replies': replies, 'best_index': 0, 'score': 0.5}
        self.wfile.write(json.dumps(response).encode('utf-8'))

    def log_message(self, format, *args):
        # keep log output concise
        print("[mock-backend] %s - - %s" % (self.address_string(), format%args))

if __name__ == '__main__':
    port = 3000
    server = HTTPServer(('0.0.0.0', port), Handler)
    print(f"Mock Python backend running at http://localhost:{port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('Shutting down')
        server.server_close()
