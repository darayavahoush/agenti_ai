import os
import json
import time
import requests
import cv2
import numpy as np
from pathlib import Path
from rapidfuzz import process, fuzz

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "data" / "images"
INDEX_PATH = DATA_DIR / "index.json"
ARASAAC_API = "https://api.arasaac.org/v1"

_index: dict = {}
_embeddings = None
_embedding_model = None


def load_index():
    global _index
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if INDEX_PATH.exists():
        with open(INDEX_PATH) as f:
            _index = json.load(f)


def save_index():
    with open(INDEX_PATH, "w") as f:
        json.dump(_index, f, indent=2)


def load_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model


def semantic_match(word: str) -> str | None:
    if not _index:
        return None
    try:
        model = load_embedding_model()
        import numpy as np
        words_in_index = list(_index.keys())
        all_words = [word] + words_in_index
        embeddings = model.encode(all_words)
        query_emb = embeddings[0]
        index_embs = embeddings[1:]
        similarities = np.dot(index_embs, query_emb) / (
            np.linalg.norm(index_embs, axis=1) * np.linalg.norm(query_emb) + 1e-9
        )
        best_idx = int(np.argmax(similarities))
        best_score = float(similarities[best_idx])
        if best_score > 0.5:
            return words_in_index[best_idx]
    except Exception as e:
        print(f"Semantic match error: {e}")
    return None


def fetch_from_arasaac(word: str) -> str | None:
    try:
        url = f"{ARASAAC_API}/pictograms/en/search/{word}"
        res = requests.get(url, timeout=8)
        if res.status_code == 200:
            results = res.json()
            if results:
                pic_id = results[0]["_id"]
                img_url = f"{ARASAAC_API}/pictograms/{pic_id}?download=false"
                img_res = requests.get(img_url, timeout=8)
                if img_res.status_code == 200:
                    filename = f"{word}.png"
                    filepath = DATA_DIR / filename
                    with open(filepath, "wb") as f:
                        f.write(img_res.content)
                    _index[word] = filename
                    save_index()
                    return filename
    except Exception as e:
        print(f"ARASAAC fetch error for {word}: {e}")
    return None


def fetch_from_web(word: str) -> str | None:
    """Fallback: scrape a real image from DuckDuckGo when ARASAAC fails."""
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.images(
                f"{word} simple clipart white background",
                max_results=5,
                type_image="clipart",
            ))
        for r in results:
            img_url = r.get("image")
            if not img_url:
                continue
            try:
                resp = requests.get(img_url, timeout=6)
                if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image"):
                    filename = f"{word}_web.png"
                    filepath = DATA_DIR / filename
                    arr = np.frombuffer(resp.content, np.uint8)
                    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                    if img is None:
                        continue
                    cv2.imwrite(str(filepath), img)
                    _index[word] = filename
                    save_index()
                    print(f"Web scraped image for: {word}")
                    return filename
            except Exception:
                continue
    except Exception as e:
        print(f"Web scrape error for {word}: {e}")
    return None




def fetch_from_pixabay(word: str) -> str | None:
    """Fallback: fetch image from Pixabay free API."""
    try:
        import os
        api_key = os.environ.get("PIXABAY_API_KEY", "")
        if not api_key:
            return None
        url = f"https://pixabay.com/api/?key={api_key}&q={word}&image_type=clipart&safesearch=true&per_page=5"
        resp = requests.get(url, timeout=6)
        if resp.status_code != 200:
            return None
        hits = resp.json().get("hits", [])
        for hit in hits:
            img_url = hit.get("webformatURL")
            if not img_url:
                continue
            try:
                img_resp = requests.get(img_url, timeout=6)
                if img_resp.status_code == 200:
                    filename = f"{word}_pixabay.png"
                    filepath = DATA_DIR / filename
                    arr = np.frombuffer(img_resp.content, np.uint8)
                    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                    if img is None:
                        continue
                    cv2.imwrite(str(filepath), img)
                    _index[word] = filename
                    save_index()
                    print(f"Pixabay image for: {word}")
                    return filename
            except Exception:
                continue
    except Exception as e:
        print(f"Pixabay error for {word}: {e}")
    return None

def _make_text_image(word: str):
    """Generate a simple white image with the word written on it as final fallback."""
    try:
        import cv2
        import numpy as np
        img = np.ones((300, 400, 3), dtype=np.uint8) * 255  # white background
        font = cv2.FONT_HERSHEY_SIMPLEX
        text = word.upper()
        font_scale = min(3.0, 10.0 / max(len(text), 1))
        thickness = max(2, int(font_scale * 2))
        (tw, th), _ = cv2.getTextSize(text, font, font_scale, thickness)
        x = (400 - tw) // 2
        y = (300 + th) // 2
        cv2.putText(img, text, (x, y), font, font_scale, (50, 50, 50), thickness, cv2.LINE_AA)
        return img
    except Exception:
        return None

def find_image(word: str) -> dict:
    if not _index:
        load_index()

    word = word.lower().strip()
    words_in_index = list(_index.keys())

    # 1. Exact match
    if word in _index:
        return {"path": str(DATA_DIR / _index[word]), "word": word, "confidence": 100, "match_type": "exact"}

    # 2. Fuzzy match — only trust high confidence (>=90) to avoid donkey→monkey style errors
    if words_in_index:
        result = process.extractOne(word, words_in_index, scorer=fuzz.token_sort_ratio)
        if result and result[1] >= 90:
            matched_word = result[0]
            return {"path": str(DATA_DIR / _index[matched_word]), "word": matched_word, "confidence": result[1], "match_type": "fuzzy"}

    # 3. Live ARASAAC API fetch
    filename = fetch_from_arasaac(word)
    if filename:
        return {"path": str(DATA_DIR / filename), "word": word, "confidence": 95, "match_type": "arasaac"}

    # 4. Web scrape fallback (DuckDuckGo)
    filename = fetch_from_web(word)
    if filename:
        return {"path": str(DATA_DIR / filename), "word": word, "confidence": 85, "match_type": "web"}

    # 5. Semantic match from existing index
    matched = semantic_match(word)
    if matched:
        return {"path": str(DATA_DIR / _index[matched]), "word": matched, "confidence": 70, "match_type": "semantic"}

    # 6. Pixabay fallback
    filename = fetch_from_pixabay(word)
    if filename:
        return {"path": str(DATA_DIR / filename), "word": word, "confidence": 80, "match_type": "pixabay"}

    # Final fallback: generate a simple text image
    img = _make_text_image(word)
    if img is not None:
        filename = f"{word}_text.png"
        filepath = DATA_DIR / filename
        cv2.imwrite(str(filepath), img)
        return {"path": str(filepath), "word": word, "confidence": 50, "match_type": "generated"}
    return {"path": None, "word": word, "confidence": 0, "match_type": "none"}


def parse_attributes(phrase: str) -> dict:
    COLORS = ["red", "blue", "green", "yellow", "orange", "purple",
              "pink", "white", "black", "brown", "grey", "gray"]
    SIZES = ["big", "large", "small", "tiny", "huge", "little"]
    words = phrase.lower().strip().split()
    color, size, obj_words = None, None, []
    for w in words:
        if w in COLORS and color is None:
            color = w
        elif w in SIZES and size is None:
            size = w
        else:
            obj_words.append(w)
    # Use last noun as object if multiple words
    obj = " ".join(obj_words) if obj_words else phrase
    return {"object": obj, "color": color, "size": size}


def make_transparent(img):
    """Remove background using floodfill from corners — works on any bg colour."""
    rgba = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
    h, w = img.shape[:2]
    
    # Floodfill mask needs to be 2px larger
    flood_mask = np.zeros((h + 2, w + 2), np.uint8)
    img_copy = img.copy()
    
    # Flood from all 4 corners to catch full background
    for corner in [(0, 0), (0, w-1), (h-1, 0), (h-1, w-1)]:
        cv2.floodFill(img_copy, flood_mask, (corner[1], corner[0]),
                      (255, 0, 255), loDiff=(25, 25, 25), upDiff=(25, 25, 25))
    
    # Pixels filled = background
    bg_mask = (img_copy[:,:,0] == 255) & (img_copy[:,:,1] == 0) & (img_copy[:,:,2] == 255)
    rgba[:,:,3][bg_mask] = 0
    return rgba


def apply_color(image_path: str, color_name: str):
    from sklearn.cluster import KMeans

    COLOR_TARGETS = {
        "red":    (0,   200, 60),
        "orange": (15,  210, 70),
        "yellow": (30,  220, 80),
        "green":  (60,  200, 60),
        "blue":   (120, 210, 70),
        "purple": (150, 200, 60),
        "pink":   (170, 180, 80),
        "brown":  (10,  180, 50),
        "black":  (0,   0,   15),
        "white":  (0,   0,   240),
        "grey":   (0,   0,   128),
        "gray":   (0,   0,   128),
    }

    img = cv2.imread(image_path)
    if img is None:
        return None
    target = COLOR_TARGETS.get(color_name)
    if target is None:
        return img

    h, w = img.shape[:2]
    target_hue, target_sat, target_val_base = target

    # Step 1: floodfill to isolate subject
    flood_mask = np.zeros((h+2, w+2), np.uint8)
    img_copy = img.copy()
    for corner in [(0,0),(0,w-1),(h-1,0),(h-1,w-1)]:
        cv2.floodFill(img_copy, flood_mask, (corner[1],corner[0]),
                      (255,0,255), loDiff=(25,25,25), upDiff=(25,25,25))
    bg_mask = (img_copy[:,:,0]==255) & (img_copy[:,:,1]==0) & (img_copy[:,:,2]==255)
    subject_mask = ~bg_mask

    # Step 2: get subject pixels
    subject_pixels = img[subject_mask]
    if len(subject_pixels) == 0:
        return img

    # Step 3: k-means to find dominant clusters
    n_clusters = min(5, len(subject_pixels) // 100 + 1)
    hsv_full = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
    subject_hsv = hsv_full[subject_mask]

    try:
        km = KMeans(n_clusters=n_clusters, n_init=3, max_iter=50, random_state=0)
        km.fit(subject_hsv)
        labels = km.labels_
        centers = km.cluster_centers_
    except Exception:
        # Fallback: direct remap
        hsv_full[:,:,0][subject_mask] = target_hue
        hsv_full[:,:,1][subject_mask] = target_sat
        hsv_full = np.clip(hsv_full, 0, 255).astype(np.uint8)
        return cv2.cvtColor(hsv_full, cv2.COLOR_HSV2BGR)

    # Step 4: remap each cluster preserving relative brightness
    result_hsv = hsv_full.copy()
    subject_indices = np.where(subject_mask)

    # Get brightness range for normalisation
    orig_vals = subject_hsv[:, 2]
    val_min, val_max = orig_vals.min(), orig_vals.max()
    val_range = max(val_max - val_min, 1)

    for i, px_label in enumerate(labels):
        orig_v = subject_hsv[i, 2]
        # Normalise brightness 0-1 then scale to target range
        norm_v = (orig_v - val_min) / val_range
        new_v = target_val_base + norm_v * (255 - target_val_base) * 0.6

        row, col = subject_indices[0][i], subject_indices[1][i]
        result_hsv[row, col, 0] = target_hue
        result_hsv[row, col, 1] = target_sat if color_name not in ("black","white","grey","gray") else 0
        result_hsv[row, col, 2] = np.clip(new_v, 0, 255)

    # Override for achromatic colours — direct brightness remap is more reliable
    if color_name == "black":
        orig_v = subject_hsv[:, 2]
        result_hsv_flat = result_hsv[subject_mask]
        result_hsv_flat[:, 0] = 0
        result_hsv_flat[:, 1] = 0
        result_hsv_flat[:, 2] = np.clip(orig_v * 0.1, 0, 25)
        result_hsv[subject_mask] = result_hsv_flat
    elif color_name == "white":
        result_hsv_flat = result_hsv[subject_mask]
        result_hsv_flat[:, 1] = 0
        result_hsv_flat[:, 2] = 240
        result_hsv[subject_mask] = result_hsv_flat
    elif color_name in ("grey", "gray"):
        orig_v = subject_hsv[:, 2]
        result_hsv_flat = result_hsv[subject_mask]
        result_hsv_flat[:, 1] = 0
        result_hsv_flat[:, 2] = np.clip(orig_v * 0.5 + 60, 80, 180)
        result_hsv[subject_mask] = result_hsv_flat

    result_hsv = np.clip(result_hsv, 0, 255).astype(np.uint8)
    return cv2.cvtColor(result_hsv, cv2.COLOR_HSV2BGR)


def apply_size(image_path: str, size: str):
    SCALE = {"big": 1.4, "large": 1.4, "huge": 1.6, "small": 0.7, "tiny": 0.5, "little": 0.6}
    img = cv2.imread(image_path)
    if img is None:
        return None
    scale = SCALE.get(size, 1.0)
    h, w = img.shape[:2]
    return cv2.resize(img, (int(w * scale), int(h * scale)))


EMOTION_WORDS = {
    "happy", "sad", "angry", "scared", "surprised", "excited",
    "tired", "confused", "proud", "worried", "calm", "nervous"
}

def get_image_for_phrase(phrase: str) -> dict:
    attrs = parse_attributes(phrase)
    words = phrase.lower().strip().split()

    # Detect if phrase has an emotion modifier + object (e.g. "angry lemon")
    emotion = None
    obj_words = []
    for w in words:
        if w in EMOTION_WORDS and emotion is None:
            emotion = w
        elif w not in [attrs.get("color"), attrs.get("size")] or attrs.get("color") is None:
            if w not in (attrs.get("color") or "").split() and w not in (attrs.get("size") or "").split():
                obj_words.append(w)

    # Strip emotion from object if present
    object_str = attrs["object"]
    if emotion and object_str.startswith(emotion):
        object_str = object_str[len(emotion):].strip()
    if not object_str:
        object_str = attrs["object"]

    # Build images list
    images = []

    # Emotion image
    if emotion:
        emotion_match = find_image(emotion)
        if emotion_match["path"]:
            img = cv2.imread(emotion_match["path"])
            if img is not None:
                img = make_transparent(img)
                _, buf = cv2.imencode(".png", img)
                images.append({
                    "label": emotion,
                    "image_bytes": buf.tobytes(),
                    "match_type": emotion_match["match_type"]
                })

    # Main object image
    match = find_image(object_str)
    if match["path"]:
        if attrs["color"]:
            img = apply_color(match["path"], attrs["color"])
        elif attrs["size"]:
            img = apply_size(match["path"], attrs["size"])
        else:
            img = cv2.imread(match["path"])

        if img is not None:
            img = make_transparent(img)
            _, buf = cv2.imencode(".png", img)
            images.append({
                "label": match["word"],
                "path": match["path"],
                "image_bytes": buf.tobytes(),
                "match_type": match["match_type"]
            })

    if not images:
        return {"found": False, "phrase": phrase, "match_type": "none", "image_bytes": None, "images": []}

    # Return primary image as before + full images list
    primary = images[-1]  # object is primary
    return {
        "found": True,
        "phrase": phrase,
        "matched_word": primary["label"],
        "match_type": primary["match_type"],
        "image_bytes": primary["image_bytes"],
        "path": primary["path"],
        "images": images,  # all images for multi-display
    }
