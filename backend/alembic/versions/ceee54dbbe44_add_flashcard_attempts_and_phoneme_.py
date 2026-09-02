"""add flashcard attempts and phoneme mastery tables

Revision ID: ceee54dbbe44
Revises: f2f2f66929d3
Create Date: 2026-08-15 19:02:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'ceee54dbbe44'
down_revision = 'f2f2f66929d3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Already included in 000baseline0_baseline_schema.py."""
    pass


def downgrade():
    op.drop_index(op.f('ix_flashcard_phoneme_mastery_phoneme'), table_name='flashcard_phoneme_mastery')
    op.drop_index(op.f('ix_flashcard_phoneme_mastery_patient_id'), table_name='flashcard_phoneme_mastery')
    op.drop_table('flashcard_phoneme_mastery')

    op.drop_index(op.f('ix_flashcard_attempts_created_at'), table_name='flashcard_attempts')
    op.drop_index(op.f('ix_flashcard_attempts_target_word'), table_name='flashcard_attempts')
    op.drop_index(op.f('ix_flashcard_attempts_theme_id'), table_name='flashcard_attempts')
    op.drop_index(op.f('ix_flashcard_attempts_session_id'), table_name='flashcard_attempts')
    op.drop_index(op.f('ix_flashcard_attempts_patient_id'), table_name='flashcard_attempts')
    op.drop_table('flashcard_attempts')
