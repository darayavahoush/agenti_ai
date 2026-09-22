"""
routers/flashcards/themes.py — Groups the flashcard word list into
kid-facing themes. This dict is the actual source of truth for which
words exist as flashcards; router.py resolves each word's image via
app.services.image.matcher.get_image_for_phrase(), which tries (in
order) the shared local image cache, ARASAAC's pictogram API, Pixabay,
a DuckDuckGo image fallback, then a generated text card -- so a word
listed here doesn't need a pre-downloaded picture to work. See
router.py's _word_payload for why the old "word must already be in
data/flashcard_images/index.json" gate was removed: it silently hid
every word below, since that index only ever had 132 entries.
"""

THEMES = {
    "core_words":        {"name": "Core Words",        "emoji": "💬", "words": ["eat","drink","sleep","run","jump","sit","stand","walk","read","write","play","cry","laugh","sing","clap","wave","hug","dance","swim","climb","throw","catch","push","pull","open","close","give","take","look","listen"]},
    "safari_animals":    {"name": "Safari Animals",     "emoji": "🦁", "words": ["elephant","lion","tiger","monkey","zebra","giraffe","hippo","rhino","cheetah","gorilla","leopard","crocodile"]},
    "birds":             {"name": "Birds",              "emoji": "🐦", "words": ["bird","parrot","duck","owl","eagle","peacock","penguin","sparrow","crow","swan","rooster","hen"]},
    "sea_animals":       {"name": "Sea Animals",        "emoji": "🐬", "words": ["octopus","shark","dolphin","whale","crab","fish","starfish","seahorse","jellyfish","turtle","squid","lobster","seal"]},
    "insects":           {"name": "Insects",            "emoji": "🐝", "words": ["ant","bee","ladybug","mosquito","butterfly","spider","fly","grasshopper","caterpillar","dragonfly","snail","worm","cricket"]},
    "fruits":            {"name": "Fruits",             "emoji": "🍎", "words": ["apple","banana","mango","grapes","orange","strawberry","watermelon","pineapple","papaya","peach","pear","cherry","kiwi","lemon","coconut"]},
    "vegetables":        {"name": "Vegetables",         "emoji": "🥕", "words": ["carrot","onion","potato","tomato","cabbage","cucumber","pumpkin","corn","peas","spinach","eggplant","beetroot","radish","garlic"]},
    "food":              {"name": "Food",               "emoji": "🍞", "words": ["bread","rice","milk","water","egg","cup","butter","cheese","sugar","salt","honey","juice","tea","coffee","noodles","soup","cake","cookie","sandwich","pizza"]},
    "school_supplies":   {"name": "School Supplies",    "emoji": "✏", "words": ["pen","pencil","paper","book","bag","eraser","ruler","scissors","glue","crayon","notebook","marker","sharpener","backpack","globe"]},
    "music":             {"name": "Music",              "emoji": "🎸", "words": ["guitar","piano","drum","trumpet","violin","flute","xylophone","microphone","headphones","tambourine","harmonica","bell","whistle"]},
    "community_helpers": {"name": "Community Helpers",  "emoji": "👩", "words": ["teacher","doctor","police","firefighter","farmer","nurse","dentist","chef","pilot","postman","mechanic","tailor","soldier","vet"]},
    "living_room":       {"name": "Living Room",        "emoji": "🛋", "words": ["chair","table","window","door","sofa","television","fan","curtain","carpet","mirror","painting","shelf","cushion"]},
    "bedroom":           {"name": "Bedroom",            "emoji": "🛏", "words": ["bed","lamp","clock","teddybear","pillow","blanket","wardrobe","mattress","nightlight","slipper","quilt","hanger"]},
    "bathroom":          {"name": "Bathroom",           "emoji": "🛁", "words": ["toilet","bathtub","toothbrush","shower","soap","towel","sink","comb","toothpaste","bucket","mug","shampoo"]},
    "numbers":           {"name": "Numbers",            "emoji": "🔢", "words": ["one","two","three","four","five"]},
    "ten_plus":          {"name": "Ten+",               "emoji": "🔟", "words": ["six","seven","eight","nine","ten"]},
    "shapes":            {"name": "Shapes",             "emoji": "⭐", "words": ["circle","square","triangle","star","diamond","rectangle","oval","heart","pentagon","hexagon"]},
    "colors":            {"name": "Colors",             "emoji": "🎨", "words": ["black","blue","green","purple","red","white","yellow","pink","brown","grey"]},
    "body_parts":        {"name": "Body Parts",         "emoji": "🖐", "words": ["ear","eye","foot","hair","hand","head","mouth","nose","cheek","chin","elbow","knee","shoulder","finger","toe","leg","arm","tongue","teeth"]},
    "family":            {"name": "Family",             "emoji": "👨‍👩‍👧", "words": ["baby","boy","girl","father","mother","grandfather","grandmother","sister","brother","uncle","aunt","cousin"]},
    "feelings":          {"name": "Feelings",           "emoji": "😊", "words": ["angry","happy","sad","scared","surprised","excited","tired","shy","proud","worried","calm","confused","bored","sleepy"]},
    "farm_pets":         {"name": "Farm & Pets",        "emoji": "🐶", "words": ["cat","cow","dog","goat","horse","rabbit","sheep","pig","donkey","puppy","kitten"]},
    "nature":            {"name": "Nature",             "emoji": "🌳", "words": ["flower","moon","sun","tree","cloud","rain","rainbow","mountain","river","grass","leaf","rock"]},
    "places":            {"name": "Places",             "emoji": "🏠", "words": ["house","school","park","hospital","market","zoo","library","farm","beach"]},
    "vehicles":          {"name": "Vehicles",           "emoji": "🚗", "words": ["bus","car","train","bicycle","airplane","boat","truck","helicopter","scooter"]},
    "toys":              {"name": "Toys",               "emoji": "🧸", "words": ["ball","kite","doll","blocks","balloon","puzzle"]},
}


def list_themes() -> list:
    return [
        {"id": theme_id, "name": t["name"], "emoji": t["emoji"], "word_count": len(t["words"])}
        for theme_id, t in THEMES.items()
    ]


def words_for_theme(theme_id: str) -> list:
    t = THEMES.get(theme_id)
    return list(t["words"]) if t else []


def all_words() -> list:
    """Every flashcard word across every theme, for /random-word's
    full-random fallback (previously read data/flashcard_images/index.json
    directly, which meant "fully random" only ever picked from the 132
    words that already had a locally cached image)."""
    out = []
    for t in THEMES.values():
        out.extend(t["words"])
    return out


def theme_for_word(word: str) -> str | None:
    for theme_id, t in THEMES.items():
        if word in t["words"]:
            return theme_id
    return None
