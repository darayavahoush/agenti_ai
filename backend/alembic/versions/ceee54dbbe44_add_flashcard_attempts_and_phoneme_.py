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


def upgrade():
    op.create_table(
        'flashcard_attempts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('theme_id', sa.String(length=50), nullable=True),
        sa.Column('target_word', sa.String(length=100), nullable=False),
        sa.Column('character', sa.String(length=50), nullable=True),
        sa.Column('language', sa.String(length=20), nullable=False),
        sa.Column('transcript', sa.String(length=255), nullable=True),
        sa.Column('phoneme_matches', sa.JSON(), nullable=False),
        sa.Column('accuracy', sa.Float(), nullable=False),
        sa.Column('composite_score', sa.Float(), nullable=False),
        sa.Column('attempt_number', sa.Integer(), nullable=False),
        sa.Column('repeat_needed', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['patient_id'], ['breathquest_patients.id'], name=op.f('flashcard_attempts_patient_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('flashcard_attempts_pkey')),
    )
    op.create_index(op.f('ix_flashcard_attempts_patient_id'), 'flashcard_attempts', ['patient_id'], unique=False)
    op.create_index(op.f('ix_flashcard_attempts_session_id'), 'flashcard_attempts', ['session_id'], unique=False)
    op.create_index(op.f('ix_flashcard_attempts_theme_id'), 'flashcard_attempts', ['theme_id'], unique=False)
    op.create_index(op.f('ix_flashcard_attempts_target_word'), 'flashcard_attempts', ['target_word'], unique=False)
    op.create_index(op.f('ix_flashcard_attempts_created_at'), 'flashcard_attempts', ['created_at'], unique=False)

    op.create_table(
        'flashcard_phoneme_mastery',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('phoneme', sa.String(length=10), nullable=False),
        sa.Column('attempts_count', sa.Integer(), nullable=False),
        sa.Column('correct_count', sa.Integer(), nullable=False),
        sa.Column('accuracy', sa.Float(), nullable=False),
        sa.Column('last_word', sa.String(length=100), nullable=True),
        sa.Column('first_practiced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_practiced_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['patient_id'], ['breathquest_patients.id'], name=op.f('flashcard_phoneme_mastery_patient_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('flashcard_phoneme_mastery_pkey')),
        sa.UniqueConstraint('patient_id', 'phoneme', name='uq_patient_phoneme'),
    )
    op.create_index(op.f('ix_flashcard_phoneme_mastery_patient_id'), 'flashcard_phoneme_mastery', ['patient_id'], unique=False)
    op.create_index(op.f('ix_flashcard_phoneme_mastery_phoneme'), 'flashcard_phoneme_mastery', ['phoneme'], unique=False)


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
