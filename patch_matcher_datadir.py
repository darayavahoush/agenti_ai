import pathlib

paths = [
    pathlib.Path("backend/app/routers/flashcards/matcher.py"),
    pathlib.Path("backend/app/services/image/matcher.py"),
]

old = 'DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "data" / "images"'
new = 'DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "images"'

for path in paths:
    src = path.read_text()
    assert old in src, f"DATA_DIR line not found verbatim in {path} -- may have drifted, aborting"
    assert src.count(old) == 1, f"expected exactly 1 match in {path}, found {src.count(old)}"
    path.write_text(src.replace(old, new))
    print(f"Patched {path}")
