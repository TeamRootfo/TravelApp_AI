import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock

from app.main import app
from app.api.v1.endpoints.package import get_package_repo, get_location_repo
from unittest.mock import patch

@pytest.fixture
def override_get_package_repo():
    mock_repo = AsyncMock()
    # Provide dummy packages back to the recommender
    mock_repo.filtered_packages.return_value = [
         {"_id": "60d5ecb8b392d70f0c0e1234", "name": "Best Wildlife Tour", "places": ["60d5ecb8b392d70f0c0e1211"]}
    ]
    app.dependency_overrides[get_package_repo] = lambda: mock_repo
    return mock_repo

@pytest.fixture
def override_get_location_repo():
    mock_loc_repo = AsyncMock()
    mock_loc_repo.get_all_tags = AsyncMock(return_value=["wildlife", "safari"])
    
    from unittest.mock import MagicMock
    # Mocking aggregate logic for vector search
    mock_aggregate_method = MagicMock()
    mock_cursor = MagicMock()
    mock_to_list = AsyncMock()
    mock_to_list.return_value = [
        {"_id": "60d5ecb8b392d70f0c0e1211", "tags": ["wildlife", "safari"], "emb_score": 0.9}
    ]
    mock_cursor.to_list = mock_to_list
    mock_aggregate_method.return_value = mock_cursor
    
    mock_loc_repo.collection.aggregate = mock_aggregate_method
    
    app.dependency_overrides[get_location_repo] = lambda: mock_loc_repo
    return mock_loc_repo

@pytest.fixture(autouse=True)
def cleanup_overrides():
    yield
    app.dependency_overrides.clear()

@pytest.mark.asyncio
@patch("app.services.package.package_recommander.embed_text", return_value=[0.1, 0.2, 0.3])
@patch("app.services.package.package_recommander.suggest_tags_from_description", return_value=["wildlife"])
@patch("app.deps.database.get_db", return_value=AsyncMock())
async def test_recommanded_packages_endpoint_success(mock_get_db, mock_suggest_tags, mock_embed_text, override_get_package_repo, override_get_location_repo):
    # Setup HTTP client with the FastAPI app instance
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/package/recommanded-packages",
            params={
                "min_price": 50.0,
                "max_price": 500.0,
                "description": "I love wildlife and safaris",
                "participant_count": 2,
                "limit": 10
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # We expect our dummy package to pass the THRESHOLD_SCORE (emb_score 0.9 * 0.7 + tags 0.3 * 1.0 = 0.93)
        assert len(data) == 1
        assert data[0]["package_id"] == "60d5ecb8b392d70f0c0e1234"
        assert "score" in data[0]

@pytest.mark.asyncio
@patch("app.services.package.package_recommander.embed_text", return_value=[0.1])
@patch("app.services.package.package_recommander.suggest_tags_from_description", return_value=["safari"])
@patch("app.deps.database.get_db", return_value=AsyncMock())
async def test_recommanded_packages_endpoint_validation_error(mock_get_db, mock_suggest, mock_embed):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Missing required parameter `description`, expecting a 422
        response = await client.post(
            "/api/v1/package/recommanded-packages",
            params={
                "min_price": -10.0, # Also invalid min_price (ge=0)
                "max_price": 500.0,
                "participant_count": 2,
                "limit": 10
            }
        )
        assert response.status_code == 422
