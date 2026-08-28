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
import pandas as pd

_g2p = G2p()


def _create_epitran(code: str):
    """Work around Panphon reading its UTF-8 data with the Windows locale."""
    original_read_csv = pd.read_csv

    def read_csv_with_utf8(*args, **kwargs):
        source = args[0] if args else kwargs.get("filepath_or_buffer")
        source_name = getattr(source, "name", "")
        if "panphon" in source_name and "feature_weights.csv" in source_name:
            kwargs["encoding"] = "cp1252"
            if args:
                args = (source_name, *args[1:])
            else:
                kwargs["filepath_or_buffer"] = source_name
        elif "panphon" in source_name:
            kwargs["encoding"] = "utf-8"
            if args:
                args = (source_name, *args[1:])
            else:
                kwargs["filepath_or_buffer"] = source_name
        return original_read_csv(*args, **kwargs)

    pd.read_csv = read_csv_with_utf8
    try:
        return epitran.Epitran(code)
    finally:
        pd.read_csv = original_read_csv


_epi_hindi = _create_epitran("hin-Deva")
_epi_kannada = _create_epitran("kan-Knda")


def get_phonemes(word: str, language: str) -> list:
    if language == "hindi":
        return list(_epi_hindi.trans_list(word))
    if language == "kannada":
        return list(_epi_kannada.trans_list(word))
    phones = _g2p(word)
    return [p.rstrip("012") for p in phones if p.strip() and p not in [" ", ""]]
