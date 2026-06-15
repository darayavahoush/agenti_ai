# Clean front-view mouth diagrams — consistent style, key feature highlighted per phoneme

def _face():
    return '''<path d="M 55 38 Q 95 28 135 38 Q 155 48 154 72 Q 152 95 120 105 Q 95 112 70 105 Q 38 95 36 72 Q 35 48 55 38Z" fill="#FDDCB5" stroke="#E8A070" stroke-width="1"/>
  <path d="M 82 52 Q 95 57 108 52" fill="none" stroke="#D08060" stroke-width="1.2" stroke-linecap="round"/>'''

def _teeth_open():
    return '''<rect x="58" y="66" width="74" height="10" rx="2" fill="white"/>
  <rect x="58" y="80" width="74" height="10" rx="2" fill="white"/>'''

def _lips_open():
    return '''<path d="M 52 68 Q 70 60 95 59 Q 120 60 138 68" fill="#CC5548" stroke="#AA3830" stroke-width="1"/>
  <path d="M 52 82 Q 70 94 95 96 Q 120 94 138 82" fill="#CC5548" stroke="#AA3830" stroke-width="1"/>'''

def _lips_sealed():
    return '''<path d="M 50 73 Q 70 65 95 64 Q 120 65 140 73" fill="#CC5548" stroke="#AA3830" stroke-width="1"/>
  <path d="M 50 78 Q 70 90 95 92 Q 120 90 140 78" fill="#CC5548" stroke="#AA3830" stroke-width="1"/>
  <path d="M 52 75 Q 95 75 138 75" stroke="#881818" stroke-width="3" fill="none" stroke-linecap="round"/>'''

def _nose_hint():
    return '<path d="M 82 52 Q 95 57 108 52" fill="none" stroke="#D08060" stroke-width="1.2" stroke-linecap="round"/>'

def _hum():
    return '''<path d="M 78 46 Q 84 41 90 46 Q 96 51 102 46 Q 108 41 114 46" stroke="#A8FF6F" stroke-width="1.5" fill="none"/>
  <path d="M 82 40 Q 88 35 95 40 Q 102 45 109 40" stroke="#A8FF6F" stroke-width="1.2" fill="none" opacity="0.6"/>'''

def _airflow():
    return '''<path d="M 140 70 L 158 66" stroke="#6AABFF" stroke-width="1.5" fill="none" stroke-linecap="round"/>
  <path d="M 140 75 L 160 75" stroke="#6AABFF" stroke-width="2" fill="none" stroke-linecap="round"/>
  <path d="M 140 80 L 158 84" stroke="#6AABFF" stroke-width="1.5" fill="none" stroke-linecap="round"/>'''

def _puff():
    return '''<path d="M 80 98 L 75 109" stroke="#6AABFF" stroke-width="1.5" fill="none" stroke-linecap="round"/>
  <path d="M 95 99 L 95 110" stroke="#6AABFF" stroke-width="2" fill="none" stroke-linecap="round"/>
  <path d="M 110 98 L 115 109" stroke="#6AABFF" stroke-width="1.5" fill="none" stroke-linecap="round"/>'''

def _voiced():
    return '<path d="M 20 75 Q 26 70 32 75 Q 38 80 44 75" stroke="#A8FF6F" stroke-width="1.5" fill="none"/>'

def _tongue_tip():
    return '''<path d="M 58 88 Q 75 82 90 76 Q 100 71 108 70" stroke="#E8756A" stroke-width="4" fill="none" stroke-linecap="round"/>
  <circle cx="108" cy="70" r="5" fill="#E8756A" stroke="#C04848" stroke-width="1.5"/>
  <circle cx="108" cy="70" r="8" fill="none" stroke="#FFD166" stroke-width="1" stroke-dasharray="2,2"/>'''

def _tongue_back():
    return '''<path d="M 58 90 Q 68 88 78 86 Q 88 84 95 80 Q 108 76 118 78" stroke="#E8756A" stroke-width="5" fill="none" stroke-linecap="round"/>
  <circle cx="115" cy="78" r="6" fill="#E8756A" stroke="#C04848" stroke-width="1.5"/>
  <circle cx="115" cy="78" r="9" fill="none" stroke="#FFD166" stroke-width="1" stroke-dasharray="2,2"/>'''

def _tongue_retroflex():
    return '''<path d="M 62 84 Q 72 80 80 76 Q 90 72 96 70 Q 100 68 101 72 Q 102 76 99 78" stroke="#E8756A" stroke-width="4" fill="none" stroke-linecap="round"/>
  <circle cx="99" cy="78" r="5" fill="#E8756A" stroke="#C04848" stroke-width="1.5"/>
  <circle cx="99" cy="78" r="9" fill="none" stroke="#FFD166" stroke-width="1" stroke-dasharray="2,2"/>'''

def _rounded_lips(size=22):
    return f'''<ellipse cx="95" cy="74" rx="{size}" ry="{int(size*0.85)}" fill="none" stroke="#CC5548" stroke-width="8"/>
  <ellipse cx="95" cy="74" rx="{int(size*0.5)}" ry="{int(size*0.45)}" fill="#1a0000" opacity="0.7"/>'''

def _teeth_on_lip():
    return '''<path d="M 52 68 Q 70 60 95 59 Q 120 60 138 68" fill="#CC5548" stroke="#AA3830" stroke-width="1"/>
  <rect x="58" y="66" width="74" height="10" rx="2" fill="white"/>
  <path d="M 52 76 Q 70 84 95 83 Q 120 82 138 74" fill="#CC5548" stroke="#AA3830" stroke-width="1.5"/>
  <path d="M 62 74 Q 75 78 90 78 Q 105 78 118 74" stroke="#FFD166" stroke-width="1.5" fill="none" stroke-dasharray="2,2"/>'''

def _wrap(content, label, badge):
    return f'''<svg viewBox="0 0 190 120" xmlns="http://www.w3.org/2000/svg">
  <rect width="190" height="120" rx="10" fill="#0D1117" stroke="#1E2B1A" stroke-width="1"/>
  <rect x="10" y="6" width="52" height="24" rx="6" fill="#1A2E14"/>
  <text x="36" y="23" text-anchor="middle" font-size="13" font-weight="700" fill="#A8FF6F" font-family="monospace">{badge}</text>
  <g transform="translate(0,4)">
    {content}
  </g>
  <text x="95" y="116" text-anchor="middle" font-size="8.5" fill="#4A5548" font-family="sans-serif">{label}</text>
</svg>'''


MOUTH_SVGS = {

"lips_closed_puff": _wrap(
    _face() + _lips_sealed(),
    "press lips together firmly",
    "/B/"
),

"lips_closed_puff_voiceless": _wrap(
    _face() + _lips_sealed() + _puff(),
    "lips shut → air puff, no voice",
    "/P/"
),

"lips_closed_hum": _wrap(
    _face() + _lips_sealed() + _hum(),
    "lips shut, hum through nose",
    "/M/"
),

"tongue_tip_up": _wrap(
    _face() + _lips_open() + _teeth_open() + _tongue_tip(),
    "tongue tip behind upper teeth",
    "/D/"
),

"tongue_tip_up_voiceless": _wrap(
    _face() + _lips_open() + _teeth_open() + _tongue_tip() + _puff(),
    "tongue tip up → air puff",
    "/T/"
),

"tongue_tip_up_hum": _wrap(
    _face() + _lips_open() + _teeth_open() + _tongue_tip() + _hum(),
    "tongue tip up, hum through nose",
    "/N/"
),

"tongue_back_up": _wrap(
    _face() + _lips_open() + _teeth_open() + _tongue_back() + _voiced(),
    "back of tongue raised",
    "/G/"
),

"tongue_back_up_voiceless": _wrap(
    _face() + _lips_open() + _teeth_open() + _tongue_back() + _puff(),
    "back tongue → air puff",
    "/K/"
),

"teeth_on_lip": _wrap(
    _face() + _teeth_on_lip() + _airflow(),
    "upper teeth on lower lip, blow air",
    "/F/"
),

"teeth_on_lip_voiced": _wrap(
    _face() + _teeth_on_lip() + _airflow() + _voiced(),
    "like F but voiced (buzz)",
    "/V/"
),

"teeth_together_hiss": _wrap(
    _face() + _lips_open() + '''
  <rect x="58" y="66" width="74" height="9" rx="2" fill="white"/>
  <rect x="58" y="76" width="74" height="9" rx="2" fill="white"/>
  <path d="M 140 72 L 165 68" stroke="#6AABFF" stroke-width="3" fill="none" stroke-linecap="round"/>''',
    "teeth close, hiss through gap",
    "/S/"
),

"teeth_together_hiss_voiced": _wrap(
    _face() + _lips_open() + '''
  <rect x="58" y="66" width="74" height="9" rx="2" fill="white"/>
  <rect x="58" y="76" width="74" height="9" rx="2" fill="white"/>
  <path d="M 140 72 L 165 68" stroke="#6AABFF" stroke-width="3" fill="none" stroke-linecap="round"/>''' + _voiced(),
    "like S but voiced (buzz)",
    "/Z/"
),

"lips_rounded_push": _wrap(
    _face() + _rounded_lips(22) + '''
  <path d="M 118 70 L 148 66" stroke="#6AABFF" stroke-width="2" fill="none" stroke-linecap="round"/>
  <path d="M 118 74 L 150 74" stroke="#6AABFF" stroke-width="2.5" fill="none" stroke-linecap="round"/>
  <path d="M 118 78 L 148 82" stroke="#6AABFF" stroke-width="2" fill="none" stroke-linecap="round"/>''',
    "lips round, push air",
    "/SH/"
),

"lips_rounded_push_voiced": _wrap(
    _face() + _rounded_lips(20) + '''
  <path d="M 118 70 L 148 66" stroke="#6AABFF" stroke-width="2" fill="none" stroke-linecap="round"/>
  <path d="M 118 74 L 150 74" stroke="#6AABFF" stroke-width="2.5" fill="none" stroke-linecap="round"/>''' + _voiced(),
    "like CH but voiced",
    "/J/"
),

"tongue_between_teeth": _wrap(
    _face() + _lips_open() + '''
  <rect x="58" y="66" width="74" height="10" rx="2" fill="white"/>
  <rect x="58" y="78" width="74" height="10" rx="2" fill="white"/>
  <ellipse cx="95" cy="74" rx="22" ry="7" fill="#E8756A" stroke="#C04848" stroke-width="1.5"/>
  <path d="M 140 71 L 162 67" stroke="#6AABFF" stroke-width="1.5" fill="none" stroke-linecap="round"/>
  <path d="M 140 74 L 165 74" stroke="#6AABFF" stroke-width="2" fill="none" stroke-linecap="round"/>''',
    "tongue peeks between teeth",
    "/TH/"
),

"tongue_tip_up_sides_open": _wrap(
    _face() + _lips_open() + _teeth_open() + '''
  <path d="M 72 82 Q 82 74 90 70 Q 97 67 104 68" stroke="#E8756A" stroke-width="4" fill="none" stroke-linecap="round"/>
  <circle cx="105" cy="68" r="4" fill="#E8756A" stroke="#C04848" stroke-width="1.5"/>
  <path d="M 58 77 L 40 72" stroke="#6AABFF" stroke-width="1.5" fill="none" stroke-linecap="round"/>
  <path d="M 132 77 L 150 72" stroke="#6AABFF" stroke-width="1.5" fill="none" stroke-linecap="round"/>''',
    "tip up, air flows sides",
    "/L/"
),

"tongue_curled_lips_rounded": _wrap(
    _face() + _rounded_lips(25) + '''
  <path d="M 75 82 Q 82 78 88 76 Q 94 75 98 77 Q 103 74 100 71" stroke="#E8756A" stroke-width="3" fill="none" stroke-linecap="round"/>''',
    "lips round, tongue curled",
    "/R/"
),

"lips_rounded_open": _wrap(
    _face() + _rounded_lips(28),
    "tight circle → open wide",
    "/W/"
),

"tongue_high_slide": _wrap(
    _face() + _lips_open() + _teeth_open() + '''
  <path d="M 65 80 Q 80 74 95 73 Q 110 74 125 80" stroke="#E8756A" stroke-width="3" fill="none" stroke-linecap="round"/>
  <path d="M 95 73 L 95 85" stroke="#FFD166" stroke-width="1.5" fill="none" stroke-dasharray="2,2" stroke-linecap="round"/>''',
    "tongue high, slides down",
    "/Y/"
),

"mouth_open_breathe": _wrap(
    _face() + '''
  <path d="M 52 66 Q 70 56 95 54 Q 120 56 138 66" fill="#CC5548" stroke="#AA3830" stroke-width="1"/>
  <path d="M 52 84 Q 70 96 95 98 Q 120 96 138 84" fill="#CC5548" stroke="#AA3830" stroke-width="1"/>
  <rect x="58" y="64" width="74" height="11" rx="2" fill="white"/>
  <rect x="58" y="81" width="74" height="11" rx="2" fill="white"/>
  <ellipse cx="95" cy="75" rx="34" ry="14" fill="#1a0000" opacity="0.5"/>
  <path d="M 118 70 L 148 65" stroke="#6AABFF" stroke-width="1.5" fill="none" stroke-linecap="round"/>
  <path d="M 120 75 L 152 75" stroke="#6AABFF" stroke-width="2.5" fill="none" stroke-linecap="round"/>
  <path d="M 118 80 L 148 85" stroke="#6AABFF" stroke-width="1.5" fill="none" stroke-linecap="round"/>''',
    "mouth open, breathe out",
    "/H/"
),

"mouth_wide_open": _wrap(
    _face() + '''
  <path d="M 46 62 Q 68 50 95 48 Q 122 50 144 62" fill="#CC5548" stroke="#AA3830" stroke-width="1.5"/>
  <path d="M 46 88 Q 68 102 95 104 Q 122 102 144 88" fill="#CC5548" stroke="#AA3830" stroke-width="1.5"/>
  <rect x="52" y="60" width="86" height="11" rx="2" fill="white"/>
  <rect x="52" y="85" width="86" height="11" rx="2" fill="white"/>
  <ellipse cx="95" cy="76" rx="40" ry="18" fill="#1a0000" opacity="0.6"/>''',
    "mouth wide open, cat / flat",
    "/AE/"
),

"lips_rounded_wide": _wrap(
    _face() + _rounded_lips(30),
    "rounded open, ball / fall",
    "/AO/"
),

"mouth_half_open": _wrap(
    _face() + '''
  <path d="M 50 66 Q 70 58 95 57 Q 120 58 140 66" fill="#CC5548" stroke="#AA3830" stroke-width="1"/>
  <path d="M 50 82 Q 70 92 95 94 Q 120 92 140 82" fill="#CC5548" stroke="#AA3830" stroke-width="1"/>
  <rect x="56" y="64" width="78" height="10" rx="2" fill="white"/>
  <rect x="56" y="80" width="78" height="10" rx="2" fill="white"/>
  <ellipse cx="95" cy="74" rx="36" ry="13" fill="#1a0000" opacity="0.55"/>''',
    "half open, bed / ten",
    "/EH/"
),

"mouth_nearly_closed_smile": _wrap(
    _face() + '''
  <path d="M 50 70 Q 70 63 95 62 Q 120 63 140 70" fill="#CC5548" stroke="#AA3830" stroke-width="1"/>
  <path d="M 50 76 Q 70 82 95 83 Q 120 82 140 76" fill="#CC5548" stroke="#AA3830" stroke-width="1"/>
  <rect x="56" y="68" width="78" height="7" rx="2" fill="white"/>
  <rect x="56" y="77" width="78" height="7" rx="2" fill="white"/>
  <path d="M 62 76 Q 78 74 95 73 Q 112 74 128 76" fill="#1a0000" opacity="0.4"/>''',
    "nearly closed, sit / tip",
    "/IH/"
),

"mouth_smile_closed": _wrap(
    _face() + '''
  <path d="M 46 70 Q 65 60 95 59 Q 125 60 144 70" fill="#CC5548" stroke="#AA3830" stroke-width="1"/>
  <path d="M 46 76 Q 65 80 95 81 Q 125 80 144 76" fill="#CC5548" stroke="#AA3830" stroke-width="1"/>
  <rect x="52" y="68" width="86" height="7" rx="2" fill="white"/>
  <rect x="52" y="76" width="86" height="6" rx="2" fill="white"/>
  <path d="M 46 70 Q 44 73 46 76" stroke="#CC5548" stroke-width="2" fill="none"/>
  <path d="M 144 70 Q 146 73 144 76" stroke="#CC5548" stroke-width="2" fill="none"/>''',
    "wide smile, see / feet",
    "/IY/"
),

"lips_small_circle": _wrap(
    _face() + _rounded_lips(16),
    "tight circle, moon / food",
    "/UW/"
),

"tongue_curled_back_touch": _wrap(
    _face() + _lips_open() + _teeth_open() + _tongue_retroflex() + '''
  <text x="95" y="60" text-anchor="middle" font-size="8" fill="#FFD166" font-family="sans-serif">retroflex</text>''',
    "curl tongue tip back",
    "/RT/"
),

"tongue_curled_back_touch_voiced": _wrap(
    _face() + _lips_open() + _teeth_open() + _tongue_retroflex() + _voiced() + '''
  <text x="95" y="60" text-anchor="middle" font-size="8" fill="#FFD166" font-family="sans-serif">retroflex</text>''',
    "retroflex D — voiced",
    "/RD/"
),

}


def get_phoneme_svg(mouth_shape: str) -> str:
    return MOUTH_SVGS.get(mouth_shape, MOUTH_SVGS["mouth_half_open"])


def get_phoneme_card(phoneme: str) -> dict:
    from app.services.phoneme.data import PHONEME_DATA
    data = PHONEME_DATA.get(phoneme.upper(), {})
    if not data:
        return None
    return {
        "phoneme": phoneme,
        "ipa": data["ipa"],
        "name": data["name"],
        "example_word": data["example_word"],
        "tip": data["tip"],
        "mouth_svg": get_phoneme_svg(data["mouth_shape"]),
        "common_errors": data["common_errors"],
        "category": data["category"],
    }
