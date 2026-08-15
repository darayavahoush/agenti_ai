"""
Word -> phoneme list. English uses g2p_en (CMU-dict based), Hindi/Kannada
use epitran. Ported from speech-repeater/backend/app/main.py, where it
was a standalone function — agenti_ai's own services/phoneme/ package has
scoring (scoring.py) and drill-sequencing (drill.py) but nothing that
does this actual word->phoneme conversion, so this isn't a duplicate of
anything already in the app.
"""
from g2p_en import G2p
import epitran

_g2p = G2p()
_epi_hindi = epitran.Epitran("hin-Deva")
_epi_kannada = epitran.Epitran("kan-Knda")


def get_phonemes(word: str, language: str) -> list:
    if language == "hindi":
        return list(_epi_hindi.trans_list(word))
    if language == "kannada":
        return list(_epi_kannada.trans_list(word))
    phones = _g2p(word)
    return [p.rstrip("012") for p in phones if p.strip() and p not in [" ", ""]]
