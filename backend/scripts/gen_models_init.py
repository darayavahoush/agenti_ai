import re
from pathlib import Path

models_dir = Path(__file__).resolve().parent.parent / "app" / "models"
init_path = models_dir / "__init__.py"

lines = [
    "# Auto-populated: imports every model module so SQLAlchemy's metadata\n",
    "# has all tables registered, regardless of which specific model a\n",
    "# script or route imports directly. Prevents NoReferencedTableError on\n",
    "# cross-table FKs (e.g. BreathQuestPatient.assessment_patient_id ->\n",
    "# patients.id) when only one side's model was imported.\n",
    "# Regenerate with scripts/gen_models_init.py if new model files are added.\n\n",
]

for f in sorted(models_dir.glob("*.py")):
    if f.name == "__init__.py":
        continue
    lines.append(f"from . import {f.stem}  # noqa: F401\n")

init_path.write_text("".join(lines))
print(f"Wrote {init_path} with {len(lines) - 6} model imports:")
print(init_path.read_text())
