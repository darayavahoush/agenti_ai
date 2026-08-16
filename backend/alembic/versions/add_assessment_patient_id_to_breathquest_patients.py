"""add assessment_patient_id to breathquest_patients

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-08-15 20:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'breathquest_patients',
        sa.Column('assessment_patient_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        op.f('ix_breathquest_patients_assessment_patient_id'),
        'breathquest_patients', ['assessment_patient_id'], unique=True,
    )
    op.create_foreign_key(
        'fk_breathquest_patients_assessment_patient_id_patients',
        'breathquest_patients', 'patients',
        ['assessment_patient_id'], ['id'],
    )


def downgrade():
    op.drop_constraint('fk_breathquest_patients_assessment_patient_id_patients', 'breathquest_patients', type_='foreignkey')
    op.drop_index(op.f('ix_breathquest_patients_assessment_patient_id'), table_name='breathquest_patients')
    op.drop_column('breathquest_patients', 'assessment_patient_id')
