# Auto-populated: imports every model module so SQLAlchemy's metadata
# has all tables registered, regardless of which specific model a
# script or route imports directly. Prevents NoReferencedTableError on
# cross-table FKs (e.g. BreathQuestPatient.assessment_patient_id ->
# patients.id) when only one side's model was imported.
# Regenerate with scripts/gen_models_init.py if new model files are added.

from . import assessment_word  # noqa: F401
from . import breathquest_models  # noqa: F401
from . import flashcards_models  # noqa: F401
from . import patient  # noqa: F401
from . import retraining_models  # noqa: F401
from . import session  # noqa: F401
from . import therapist  # noqa: F401
from . import vaakmirror_models  # noqa: F401
from . import voicehurdlerace_models  # noqa: F401
