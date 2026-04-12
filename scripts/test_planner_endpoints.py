import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

from app.main import app
from app.api.v1.endpoints.planner import get_repo


@pytest.fixture
def override_get_repo():
    mock_repo = AsyncMock()
    # Mock for repo.get
    mock_repo.get = AsyncMock(return_value={
        "_id": "place_123",
        "name": "Original Place",
        "latitude": 6.9271,
        "longitude": 79.8612
    })
    
    # Mock for repo.nearby
    mock_repo.nearby = AsyncMock(return_value=[
        {
            "_id": "place_456",
            "name": "Alternative Place 1",
            "latitude": 6.9300,
            "longitude": 79.8600,
            "tags": ["park", "nature"]
        },
        {
            "_id": "place_789",
            "name": "Alternative Place 2",
            "latitude": 6.9250,
            "longitude": 79.8650,
            "tags": ["museum", "history"]
        }
    ])
    
    # Mock for repo.get_all_tags
    mock_repo.get_all_tags = AsyncMock(return_value=["park", "nature", "museum", "history"])
    
    app.dependency_overrides[get_repo] = lambda: mock_repo
    return mock_repo


@pytest.fixture(autouse=True)
def cleanup_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
@patch("app.api.v1.endpoints.planner.rank_candidate_locations")
async def test_replace_place_success(mock_rank, override_get_repo):
    # Mock rank_candidate_locations to return the candidates as they are for simplicity
    mock_rank.return_value = [
        {
            "_id": "place_456",
            "name": "Alternative Place 1",
            "score": 0.85
        },
        {
            "_id": "place_789",
            "name": "Alternative Place 2",
            "score": 0.70
        }
    ]

    payload = {
        "current_plan_places": ["place_123", "place_abc"],
        "place_to_replace_id": "place_123",
        "prompt": "I prefer nature over museums",
        "radius_m": 2000,
        "limit": 5
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/planner/replace-place", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["_id"] == "place_456"
        assert data[1]["_id"] == "place_789"
        
        # Verify repo.get was called
        override_get_repo.get.assert_called_once_with("place_123")
        
        # Verify repo.nearby was called correctly
        override_get_repo.nearby.assert_called_once()
        kwargs = override_get_repo.nearby.call_args.kwargs
        assert kwargs["anchor_id"] == "place_123"
        assert kwargs["latitude"] == 6.9271
        assert kwargs["longitude"] == 79.8612
        assert kwargs["exclude_ids"] == ["place_123", "place_abc"]


@pytest.mark.asyncio
async def test_replace_place_not_found(override_get_repo):
    override_get_repo.get.return_value = None
    
    payload = {
        "current_plan_places": ["not_found_place"],
        "place_to_replace_id": "not_found_place",
        "prompt": "change it",
        "radius_m": 5000,
        "limit": 5
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/planner/replace-place", json=payload)
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Place to replace not found"
