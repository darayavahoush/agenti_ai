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

25 categories, 776 words. Numbers and Ten+ have been merged into a
single Numbers category (1-30). Every existing word from the prior
26-category version is preserved as-is; this only adds new words on
top, so nothing already live changes id or disappears. No word repeats
across categories.
"""

THEMES = {
    "core_words":       {"name": "Core Words", "emoji": "💬", "words": ["eat","drink","sleep","run","jump","sit","stand","walk","read","write","play","cry","laugh","sing","clap","wave","hug","dance","swim","climb","throw","catch","push","pull","open","close","give","take","look","listen","fall","hop","kick","kiss","point","shout","whisper","smile","frown","hide","seek","hold","carry"]},
    "safari_animals":   {"name": "Safari Animals", "emoji": "🦁", "words": ["elephant","lion","tiger","monkey","zebra","giraffe","hippo","rhino","cheetah","gorilla","leopard","crocodile","camel","buffalo","antelope","warthog","hyena","meerkat","flamingo","ostrich","jackal","gazelle","panther","kangaroo","koala","wolf","fox","bear","panda","moose"]},
    "birds":            {"name": "Birds", "emoji": "🐦", "words": ["bird","parrot","duck","owl","eagle","peacock","penguin","sparrow","crow","swan","rooster","hen","pigeon","woodpecker","kingfisher","cuckoo","stork","heron","seagull","falcon","vulture","hummingbird","robin","canary","goose","toucan","macaw","dove","pheasant","quail"]},
    "sea_animals":      {"name": "Sea Animals", "emoji": "🐬", "words": ["octopus","shark","dolphin","whale","crab","fish","starfish","seahorse","jellyfish","turtle","squid","lobster","seal","clam","oyster","shrimp","eel","stingray","pufferfish","clownfish","urchin","anemone","otter","walrus","manatee","barracuda","reef","snapper","tuna","swordfish"]},
    "insects":          {"name": "Insects", "emoji": "🐝", "words": ["ant","bee","ladybug","mosquito","butterfly","spider","fly","grasshopper","caterpillar","dragonfly","snail","worm","cricket","moth","beetle","termite","wasp","cockroach","centipede","millipede","firefly","cicada","aphid","earwig","stinkbug","scorpion","tick","flea","weevil","mantis"]},
    "fruits":           {"name": "Fruits", "emoji": "🍎", "words": ["apple","banana","mango","grapes","orange","strawberry","watermelon","pineapple","papaya","peach","pear","cherry","kiwi","lemon","coconut","guava","plum","apricot","fig","pomegranate","blueberry","raspberry","blackberry","lychee","dragonfruit","custardapple","jackfruit","melon","dates","gooseberry"]},
    "vegetables":       {"name": "Vegetables", "emoji": "🥕", "words": ["carrot","onion","potato","tomato","cabbage","cucumber","pumpkin","corn","peas","spinach","eggplant","beetroot","radish","garlic","broccoli","cauliflower","lettuce","zucchini","turnip","sweetpotato","chilli","capsicum","okra","mushroom","asparagus","celery","leek","kale","artichoke","fennel"]},
    "food":             {"name": "Food", "emoji": "🍞", "words": ["bread","rice","milk","water","egg","cup","butter","cheese","sugar","salt","honey","juice","tea","coffee","noodles","soup","cake","cookie","sandwich","pizza","yogurt","pasta","paratha","dosa","idli","curry","dal","omelette","popcorn","chocolate","icecream","pancake","waffle","toast","jam"]},
    "school_supplies":  {"name": "School Supplies", "emoji": "✏", "words": ["pen","pencil","paper","book","bag","eraser","ruler","scissors","glue","crayon","notebook","marker","sharpener","backpack","globe","chalk","blackboard","calculator","stapler","clip","folder","calendar","paint","paintbrush","palette","compass","protractor","tape","stickynote","clipboard"]},
    "music":            {"name": "Music", "emoji": "🎸", "words": ["guitar","piano","drum","trumpet","violin","flute","xylophone","microphone","headphones","tambourine","harmonica","bell","whistle","cymbal","accordion","saxophone","cello","banjo","maracas","clarinet","harp","sitar","tabla","ukulele","recorder","keyboard","organ","conductor","band","cassette"]},
    "community_helpers":{"name": "Community Helpers", "emoji": "👩", "words": ["teacher","doctor","police","firefighter","farmer","nurse","dentist","chef","pilot","postman","mechanic","tailor","soldier","vet","engineer","scientist","artist","lawyer","judge","electrician","plumber","carpenter","barber","waiter","librarian","cashier","guard","fisherman","cleaner","journalist"]},
    "living_room":      {"name": "Living Room", "emoji": "🛋", "words": ["chair","table","window","door","sofa","television","fan","curtain","carpet","mirror","painting","shelf","cushion","rug","bookshelf","remote","speaker","vase","photoframe","armchair","stool","fireplace","bin","switch","plug","couch","coffeetable","blinds","doormat","ottoman"]},
    "bedroom":          {"name": "Bedroom", "emoji": "🛏", "words": ["bed","lamp","clock","teddybear","pillow","blanket","wardrobe","mattress","nightlight","slipper","quilt","hanger","dresser","closet","poster","desk","bunkbed","cradle","mobile","nightstand","pajamas","socks","alarm","diary","ladder","canopy","beanbag","headboard","footstool","dollbed"]},
    "bathroom":         {"name": "Bathroom", "emoji": "🛁", "words": ["toilet","bathtub","toothbrush","shower","soap","towel","sink","comb","toothpaste","bucket","mug","shampoo","faucet","drain","mat","hairdryer","razor","brush","scale","tissue","sponge","showercap","robe","plunger","cabinet","laundrybasket","hook","hotwater","coldwater","bathslippers"]},
    "numbers":          {"name": "Numbers", "emoji": "🔢", "words": ["one","two","three","four","five","six","seven","eight","nine","ten","eleven","twelve","thirteen","fourteen","fifteen","sixteen","seventeen","eighteen","nineteen","twenty","twentyone","twentytwo","twentythree","twentyfour","twentyfive","twentysix","twentyseven","twentyeight","twentynine","thirty"]},
    "shapes":           {"name": "Shapes", "emoji": "⭐", "words": ["circle","square","triangle","star","diamond","rectangle","oval","heart","pentagon","hexagon","cube","cylinder","cone","sphere","cross","crescent","arrow","spiral","parallelogram","trapezoid","semicircle","octagon","zigzag","rhombus","pyramid","dot","curve","ring","spike","teardrop"]},
    "colors":           {"name": "Colors", "emoji": "🎨", "words": ["black","blue","green","purple","red","white","yellow","pink","brown","grey","maroon","navy","turquoise","olive","indigo","violet","magenta","cyan","beige","tan","gold","silver","lavender","teal","mint","cream","ivory","charcoal","crimson","aqua","rust","mustard"]},
    "body_parts":       {"name": "Body Parts", "emoji": "🖐", "words": ["ear","eye","foot","hair","hand","head","mouth","nose","cheek","chin","elbow","knee","shoulder","finger","toe","leg","arm","tongue","teeth","neck","chest","back","stomach","waist","wrist","ankle","thumb","eyebrow","eyelash","forehead","lip","jaw","heel","palm","fist"]},
    "family":           {"name": "Family", "emoji": "👨‍👩‍👧", "words": ["baby","boy","girl","father","mother","grandfather","grandmother","sister","brother","uncle","aunt","cousin","nephew","niece","stepbrother","stepsister","twin","husband","wife","relative","kids","parents","elder","youngest","stepmother","stepfather","grandchild","grownup","toddler","newborn"]},
    "feelings":         {"name": "Feelings", "emoji": "😊", "words": ["angry","happy","sad","scared","surprised","excited","tired","shy","proud","worried","calm","confused","bored","sleepy","jealous","lonely","brave","nervous","curious","grumpy","hopeful","embarrassed","relaxed","stressed","cheerful","disappointed","frustrated","loving","peaceful","grateful"]},
    "farm_pets":        {"name": "Farm & Pets", "emoji": "🐶", "words": ["cat","cow","dog","goat","horse","rabbit","sheep","pig","donkey","puppy","kitten","duckling","calf","lamb","foal","bull","ox","mule","hamster","guineapig","goldfish","tortoise","mouse","chick","llama","peahen","ram","gosling","fawn","piglet"]},
    "nature":           {"name": "Nature", "emoji": "🌳", "words": ["flower","moon","sun","tree","cloud","rain","rainbow","mountain","river","grass","leaf","rock","sky","lake","ocean","wind","snow","storm","thunder","lightning","volcano","desert","forest","valley","island","waterfall","pond","soil","pebble","cave","cliff"]},
    "places":           {"name": "Places", "emoji": "🏠", "words": ["house","school","park","hospital","market","zoo","library","farm","beach","temple","church","mosque","office","bank","station","airport","restaurant","supermarket","playground","museum","cinema","stadium","garden","bridge","tower","factory","bakery","mall","clinic","gym"]},
    "vehicles":         {"name": "Vehicles", "emoji": "🚗", "words": ["bus","car","train","bicycle","airplane","boat","truck","helicopter","scooter","motorbike","tractor","ambulance","firetruck","van","ship","submarine","rocket","jeep","tram","rickshaw","cart","skateboard","wheelchair","crane","bulldozer","tanker","ferry","sled","jetski","glider"]},
    "toys":             {"name": "Toys", "emoji": "🧸", "words": ["ball","kite","doll","blocks","balloon","puzzle","robot","yoyo","spinner","dollhouse","trampoline","swing","seesaw","slide","rockinghorse","marbles","toycar","trainset","drumtoy","boardgame","cards","frisbee","jumprope","tricycle","stackingrings","pinwheel","sandbucket","xylophonetoy","toyplane","waterballoon"]},
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
