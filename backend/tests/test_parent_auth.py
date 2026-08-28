import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from app.breathquest_core.security import create_refresh_token
from app.models.breathquest_models import RefreshToken

@pytest.mark.asyncio
async def test_create_refresh_token_converts_str_to_uuid():
    # Mock database session
    mock_db = AsyncMock()
    
    owner_id_str = str(uuid.uuid4())
    owner_kind = "parent"
    
    # Call create_refresh_token with string ID
    raw_token = await create_refresh_token(mock_db, owner_kind, owner_id_str)
    
    # Assert raw token is returned
    assert isinstance(raw_token, str)
    assert len(raw_token) > 0
    
    # Verify db.add was called with RefreshToken containing a uuid.UUID owner_id
    assert mock_db.add.called
    added_token = mock_db.add.call_args[0][0]
    assert isinstance(added_token, RefreshToken)
    assert added_token.owner_id == uuid.UUID(owner_id_str)
    assert added_token.owner_kind == owner_kind
    
    # Verify db.flush was called
    assert mock_db.flush.called

@pytest.mark.asyncio
async def test_create_refresh_token_handles_uuid_directly():
    mock_db = AsyncMock()
    owner_id_uuid = uuid.uuid4()
    owner_kind = "patient"
    
    raw_token = await create_refresh_token(mock_db, owner_kind, owner_id_uuid)
    
    assert mock_db.add.called
    added_token = mock_db.add.call_args[0][0]
    assert added_token.owner_id == owner_id_uuid
