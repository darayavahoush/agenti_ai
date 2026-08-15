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

def fetch_from_arasaac_colored(word: str, color: str) -> str | None:
    """Fetch ARASAAC pictogram with color applied via their API."""
    try:
        url = f"{ARASAAC_API}/pictograms/en/search/{word}"
        res = requests.get(url, timeout=8)
        if res.status_code == 200:
            results = res.json()
            if results:
                pic_id = results[0]["_id"]
                # ARASAAC supports color parameter directly
                img_url = f"{ARASAAC_API}/pictograms/{pic_id}?download=false&color=true"
                img_res = requests.get(img_url, timeout=8)
                if img_res.status_code == 200:
                    filename = f"{color}_{word}_arasaac.png"
                    filepath = DATA_DIR / filename
                    with open(filepath, "wb") as f:
                        f.write(img_res.content)
                    return filename
    except Exception as e:
        print(f"ARASAAC color fetch error for {word}: {e}")
    return None



def fetch_from_wikimedia(word: str) -> str | None:
    """Fetch clipart/illustration from Wikimedia Commons — free, no key needed."""
    try:
        search_query = f"{word} clipart"
        url = (
            f"https://commons.wikimedia.org/w/api.php"
            f"?action=query&generator=search&gsrnamespace=6"
            f"&gsrsearch={requests.utils.quote(search_query)}&gsrlimit=5"
            f"&prop=imageinfo&iiprop=url|mime&format=json"
        )
        res = requests.get(url, timeout=4, headers={"User-Agent": "VaakSiddhi/1.0"})
        if res.status_code != 200:
            return None
        pages = res.json().get("query", {}).get("pages", {})
        for page in pages.values():
            info = page.get("imageinfo", [{}])[0]
            img_url = info.get("url", "")
            mime = info.get("mime", "")
            # Only use PNG/JPG — skip SVG and PDF
            if not img_url or mime not in ("image/png", "image/jpeg"):
                continue
            try:
                img_res = requests.get(img_url, timeout=5, headers={"User-Agent": "VaakSiddhi/1.0"})
                if img_res.status_code == 200:
                    filename = f"{word.replace(' ', '_')}_wikimedia.png"
                    filepath = DATA_DIR / filename
                    arr = np.frombuffer(img_res.content, np.uint8)
                    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                    if img is None:
                        continue
                    cv2.imwrite(str(filepath), img)
                    print(f"Wikimedia image for: {word}")
                    return filename
            except Exception:
                continue
    except Exception as e:
        print(f"Wikimedia error for {word}: {e}")
    return None

def fetch_from_openclipart(word: str) -> str | None:
    """Fetch SVG clipart from OpenClipart API and rasterize to PNG."""
    try:
        url = f"https://openclipart.org/search/json/?query={word}&amount=5&offset=0"
        res = requests.get(url, timeout=4, headers={"User-Agent": "VaakSiddhi/1.0"})
        if res.status_code != 200:
            return None
        results = res.json().get("resources", [])
        for r in results:
            svg_url = r.get("svg", {}).get("url")
            if not svg_url:
                continue
            try:
                svg_res = requests.get(svg_url, timeout=8)
                if svg_res.status_code == 200:
                    # Rasterize SVG to PNG using cairosvg if available, else skip
                    try:
                        import cairosvg
                        png_bytes = cairosvg.svg2png(bytestring=svg_res.content, output_width=400, output_height=400)
                        filename = f"{word}_openclipart.png"
                        filepath = DATA_DIR / filename
                        with open(filepath, "wb") as f:
                            f.write(png_bytes)
                        _index[word] = filename
                        save_index()
                        print(f"OpenClipart image for: {word}")
                        return filename
                    except ImportError:
                        # cairosvg not available — save SVG directly and convert with cv2
                        import tempfile
                        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as tmp:
                            tmp.write(svg_res.content)
                            tmp_path = tmp.name
                        # Try imagemagick via subprocess
                        import subprocess, os
                        png_path = tmp_path.replace(".svg", ".png")
                        result = subprocess.run(["convert", "-background", "none", tmp_path, png_path], capture_output=True, timeout=10)
                        if result.returncode == 0 and os.path.exists(png_path):
                            filename = f"{word}_openclipart.png"
                            filepath = DATA_DIR / filename
                            import shutil
                            shutil.copy(png_path, filepath)
                            _index[word] = filename
                            save_index()
                            return filename
            except Exception:
                continue
    except Exception as e:
        print(f"OpenClipart error for {word}: {e}")
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





def fetch_from_pixabay_hq(word: str) -> str | None:
    """Fetch high quality image from Pixabay — filters for larger images only."""
    try:
        import os
        api_key = os.environ.get("PIXABAY_API_KEY", "")
        if not api_key:
            return None
        url = f"https://pixabay.com/api/?key={api_key}&q={word}&image_type=vector&safesearch=true&per_page=10&min_width=500&min_height=500&order=popular"
        resp = requests.get(url, timeout=6)
        if resp.status_code != 200:
            return None
        hits = resp.json().get("hits", [])
        for hit in hits:
            # Prefer larger web format
            img_url = hit.get("webformatURL")
            w, h = hit.get("webformatWidth", 0), hit.get("webformatHeight", 0)
            if not img_url or w < 300 or h < 300:
                continue
            try:
                img_resp = requests.get(img_url, timeout=6)
                if img_resp.status_code == 200:
                    filename = f"{word.replace(' ', '_')}_pixabay_hq.png"
                    filepath = DATA_DIR / filename
                    arr = np.frombuffer(img_resp.content, np.uint8)
                    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                    if img is None:
                        continue
                    cv2.imwrite(str(filepath), img)
                    print(f"Pixabay HQ image for: {word}")
                    return filename
            except Exception:
                continue
    except Exception as e:
        print(f"Pixabay HQ error for {word}: {e}")
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

    # 4. Wikimedia Commons
    filename = fetch_from_wikimedia(word)
    if filename:
        return {"path": str(DATA_DIR / filename), "word": word, "confidence": 88, "match_type": "wikimedia"}

    # 5. Pixabay vector
    filename = fetch_from_pixabay_hq(word)
    if filename:
        return {"path": str(DATA_DIR / filename), "word": word, "confidence": 82, "match_type": "pixabay_vector"}

    # 6. Semantic match from existing index
    matched = semantic_match(word)
    if matched:
        return {"path": str(DATA_DIR / _index[matched]), "word": matched, "confidence": 70, "match_type": "semantic"}

    # 7. DuckDuckGo web scrape (last resort before text)
    filename = fetch_from_web(word)
    if filename:
        return {"path": str(DATA_DIR / filename), "word": word, "confidence": 60, "match_type": "web"}

    # 8. Pixabay general fallback
    filename = fetch_from_pixabay(word)
    if filename:
        return {"path": str(DATA_DIR / filename), "word": word, "confidence": 55, "match_type": "pixabay"}

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

COLORS = ["red", "blue", "green", "yellow", "orange", "purple",
          "pink", "white", "black", "brown", "grey", "gray", "golden", "silver",
          "cyan", "magenta", "violet", "indigo", "teal", "turquoise", "maroon",
          "navy", "olive", "coral", "salmon", "beige", "cream", "ivory",
          "gold", "bronze", "copper", "lime", "mint", "lavender", "peach"]
SIZES = ["big", "large", "small", "tiny", "huge", "little"]
STOP_WORDS = {"a", "an", "the", "is", "are", "was", "were", "this", "that", "these",
              "those", "it", "its", "of", "in", "on", "at", "to", "for", "with", "and", "or"}

def extract_key_words(phrase: str) -> dict:
    import nltk
    words = phrase.lower().strip().split()
    words = [w for w in words if w not in STOP_WORDS]
    color = None
    adjectives = []
    nouns = []
    remaining = []
    for w in words:
        if w in COLORS and color is None:
            color = w
        else:
            remaining.append(w)
    try:
        tagged = nltk.pos_tag(remaining)
        for word, tag in tagged:
            if tag.startswith("NN"):
                nouns.append(word)
            elif tag.startswith("JJ") or tag.startswith("VBG"):
                adjectives.append(word)
    except Exception:
        nouns = remaining
    return {
        "color": color,
        "adjective": adjectives[0] if adjectives else None,
        "nouns": nouns,
        "primary_noun": nouns[-1] if nouns else (remaining[-1] if remaining else phrase),
        "size": next((w for w in words if w in ["big","large","small","tiny","huge","little"]), None),
    }


def _img_to_b64(img):
    if img is None:
        return None
    img = make_transparent(img)
    _, buf = cv2.imencode(".png", img)
    return buf.tobytes()


def _color_swatch_bytes(color_name: str):
    COLOR_BGR = {
        "red": (0, 0, 210), "blue": (210, 80, 0), "green": (0, 180, 0),
        "yellow": (0, 220, 220), "orange": (0, 140, 255), "purple": (180, 0, 180),
        "pink": (180, 100, 220), "white": (240, 240, 240), "black": (30, 30, 30),
        "brown": (30, 80, 130), "grey": (150, 150, 150), "gray": (150, 150, 150),
        "golden": (0, 200, 230), "silver": (180, 180, 190), "gold": (0, 200, 230),
        "cyan": (220, 210, 0), "magenta": (210, 0, 210), "violet": (200, 0, 150),
        "indigo": (180, 0, 80), "teal": (160, 160, 0), "turquoise": (180, 200, 0),
        "maroon": (0, 0, 130), "navy": (140, 30, 0), "olive": (0, 130, 80),
        "coral": (80, 100, 240), "salmon": (100, 130, 240), "beige": (180, 210, 230),
        "cream": (200, 230, 240), "ivory": (210, 240, 245), "bronze": (40, 110, 180),
        "copper": (60, 120, 190), "lime": (0, 220, 100), "mint": (160, 220, 170),
        "lavender": (220, 170, 200), "peach": (160, 190, 240),
    }
    bgr = COLOR_BGR.get(color_name, (128, 128, 128))
    img = np.ones((200, 200, 3), dtype=np.uint8) * 255
    cv2.circle(img, (100, 100), 80, bgr, -1)
    rgba = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
    mask = np.zeros(img.shape[:2], np.uint8)
    cv2.circle(mask, (100, 100), 80, 255, -1)
    rgba[:, :, 3] = mask
    _, buf = cv2.imencode(".png", rgba)
    return buf.tobytes()


def get_image_for_phrase(phrase: str) -> dict:
    kw = extract_key_words(phrase)
    color = kw["color"]
    adjective = kw["adjective"]
    primary_noun = kw["primary_noun"]
    nouns = kw["nouns"]
    size = kw["size"]
    images = []

    # Pure color word (e.g. "yellow", "red") — just show swatch + reference
    if color and (not primary_noun or primary_noun == color):
        images.append({
            "label": color,
            "image_bytes": _color_swatch_bytes(color),
            "image_bytes_2": None,
            "pair": False,
            "match_type": "color_swatch",
        })
        # Try to find a reference image for this color
        wiki = fetch_from_wikimedia(color)
        if wiki:
            img = cv2.imread(str(DATA_DIR / wiki))
            b = _img_to_b64(img)
            if b:
                images.append({"label": f"{color} (reference)", "image_bytes": b, "match_type": "wikimedia", "pair": False})
        if not images:
            return {"found": False, "phrase": phrase, "match_type": "none", "image_bytes": None, "images": []}
        primary = images[0]
        return {"found": True, "phrase": phrase, "matched_word": color, "match_type": primary["match_type"], "image_bytes": primary["image_bytes"], "images": images}

    if color and primary_noun:
        noun_match = find_image(primary_noun)

        # Slide 1: color swatch + plain noun side by side
        swatch_bytes = _color_swatch_bytes(color)
        plain_bytes = None
        if noun_match["path"]:
            plain_bytes = _img_to_b64(cv2.imread(noun_match["path"]))
        images.append({
            "label": f"{color} + {primary_noun}",
            "image_bytes": swatch_bytes,
            "image_bytes_2": plain_bytes,
            "pair": True,
            "label_1": color,
            "label_2": primary_noun,
            "match_type": "color_pair",
        })

        # Slide 2: Wikimedia
        wiki = fetch_from_wikimedia(primary_noun)
        if wiki:
            img = cv2.imread(str(DATA_DIR / wiki))
            b = _img_to_b64(img)
            if b:
                images.append({"label": f"{primary_noun} (reference)", "image_bytes": b, "match_type": "wikimedia", "pair": False})

        # Slide 3: artificially colored noun
        if noun_match["path"]:
            colored = apply_color(noun_match["path"], color)
            b = _img_to_b64(colored)
            if b:
                images.append({"label": f"{color} {primary_noun}", "image_bytes": b, "match_type": "colored", "pair": False})

        if not images:
            return {"found": False, "phrase": phrase, "match_type": "none", "image_bytes": None, "images": []}
        primary = images[-1]
        return {"found": True, "phrase": phrase, "matched_word": primary["label"], "match_type": primary["match_type"], "image_bytes": primary["image_bytes"], "images": images}

    if adjective and primary_noun:
        # Adjective first, then noun
        noun_match = find_image(primary_noun)
        if noun_match["path"]:
            img = apply_size(noun_match["path"], size) if size else cv2.imread(noun_match["path"])
            b = _img_to_b64(img)
            if b:
                images.insert(0, {"label": primary_noun, "image_bytes": b, "match_type": noun_match["match_type"]})
        adj_match = find_image(adjective)
        if adj_match["path"]:
            b = _img_to_b64(cv2.imread(adj_match["path"]))
            if b:
                images.insert(0, {"label": adjective, "image_bytes": b, "match_type": adj_match["match_type"]})
        if images:
            primary = images[-1]
            return {"found": True, "phrase": phrase, "matched_word": primary["label"], "match_type": primary["match_type"], "image_bytes": primary["image_bytes"], "images": images}

    if len(nouns) > 1:
        for noun in nouns[-2:]:
            match = find_image(noun)
            if match["path"]:
                b = _img_to_b64(cv2.imread(match["path"]))
                if b:
                    images.append({"label": noun, "image_bytes": b, "match_type": match["match_type"]})
        if images:
            primary = images[-1]
            return {"found": True, "phrase": phrase, "matched_word": primary["label"], "match_type": primary["match_type"], "image_bytes": primary["image_bytes"], "images": images}

    match = find_image(primary_noun)
    if match["path"]:
        img = apply_size(match["path"], size) if size else cv2.imread(match["path"])
        b = _img_to_b64(img)
        if b:
            images.append({"label": match["word"], "image_bytes": b, "match_type": match["match_type"]})
            return {"found": True, "phrase": phrase, "matched_word": match["word"], "match_type": match["match_type"], "image_bytes": b, "images": images}

    return {"found": False, "phrase": phrase, "match_type": "none", "image_bytes": None, "images": []}
