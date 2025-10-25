"""Per-criterion token-based reranker trained from reviews.json.

This module trains per-criterion token averages (e.g. factuality, clarity,
ethics) from stored reviews and provides a composite scorer that accepts
weights for each criterion to compute a single 0..1 score.
"""
import json
import re
from collections import defaultdict

_WORD_RE = re.compile(r"\w+", re.U)

_CRITERIA = ['factuality', 'clarity', 'ethics']

def _tokenize(text):
    if not text:
        return []
    return [t.lower() for t in _WORD_RE.findall(text)]


def train_from_reviews(path='reviews.json'):
    """Load reviews.json and return a dict of criterion -> token->avg_rating.

    Reviews may include a 'criteria' object (dict) with per-criterion numeric
    ratings. If a review lacks per-criterion ratings but has a top-level
    'rating', that rating is applied to all criteria.
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            reviews = json.load(f)
    except Exception:
        return {}

    sums = {c: defaultdict(float) for c in _CRITERIA}
    counts = {c: defaultdict(int) for c in _CRITERIA}

    for r in reviews:
        if not isinstance(r, dict):
            continue
        text = r.get('assistantText') or ''
        toks = set(_tokenize(text))

        # prefer per-criterion ratings if present
        criteria = r.get('criteria') if isinstance(r.get('criteria'), dict) else None
        if criteria:
            for c in _CRITERIA:
                val = criteria.get(c)
                try:
                    val = float(val)
                except Exception:
                    val = None
                if val is None:
                    # fallback to top-level rating
                    try:
                        val = float(r.get('rating'))
                    except Exception:
                        val = None
                if val is None:
                    continue
                for t in toks:
                    sums[c][t] += val
                    counts[c][t] += 1
        else:
            # no per-criterion data: apply top-level rating to all criteria
            try:
                val = float(r.get('rating'))
            except Exception:
                continue
            for c in _CRITERIA:
                for t in toks:
                    sums[c][t] += val
                    counts[c][t] += 1

    token_scores = {}
    for c in _CRITERIA:
        token_scores[c] = {}
        for t, s in sums[c].items():
            token_scores[c][t] = s / max(1, counts[c][t])

    return token_scores


def score_text(text, token_scores, weights=None):
    """Compute a weighted composite score (0..1) for the candidate text.

    token_scores is expected to be a dict: criterion -> token->avg_rating (1-5 scale).
    weights is a dict mapping criterion -> weight (weights will be normalized).

    Behavior:
    - For each criterion, compute the average of token ratings present in
      that criterion's token map. If no tokens matched for a criterion, the
      criterion score defaults to neutral (0.5).
    - Composite score is weighted sum of per-criterion scores.
    """
    toks = _tokenize(text)
    if not toks:
        return 0.5

    # normalize weights
    w = {}
    if isinstance(weights, dict):
        total = sum(float(weights.get(k, 0) or 0) for k in _CRITERIA)
        if total <= 0:
            # fallback to equal weights
            for k in _CRITERIA:
                w[k] = 1.0 / len(_CRITERIA)
        else:
            for k in _CRITERIA:
                try:
                    w[k] = float(weights.get(k, 0) or 0) / total
                except Exception:
                    w[k] = 0.0
    else:
        for k in _CRITERIA:
            w[k] = 1.0 / len(_CRITERIA)

    per_scores = {}
    any_token_found = False
    for c in _CRITERIA:
        vals = []
        c_map = token_scores.get(c, {}) if isinstance(token_scores, dict) else {}
        for t in toks:
            if t in c_map:
                vals.append(c_map[t])
        if vals:
            any_token_found = True
            avg = sum(vals) / len(vals)
            # normalize 1-5 -> 0..1
            try:
                per_scores[c] = max(0.0, min(1.0, (avg - 1.0) / 4.0))
            except Exception:
                per_scores[c] = 0.5
        else:
            per_scores[c] = 0.5

    if not any_token_found:
        return 0.5

    composite = sum(per_scores[c] * w.get(c, 0) for c in _CRITERIA)
    return max(0.0, min(1.0, composite))
