from pydantic import BaseModel
from typing import Optional
from uuid import UUID

# Create Patient
class PatientCreate(BaseModel):
    name: str
    age: int
    language: str

    gender: Optional[str] = None
    diagnosis: Optional[str] = None
    therapist_name: Optional[str] = None
    parent_contact: Optional[str] = None


# Return Patient
class PatientOut(BaseModel):
    id: UUID
    name: str
    age: int
    language: str

    class Config:
        from_attributes = True