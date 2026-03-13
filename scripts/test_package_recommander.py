import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from bson import ObjectId

from app.services.package.package_recommander import (
    calculate_tag_match_score,
    calculate_total_score_for_package,
    recommanded_packages,
    THRESHOLD_VALUE,
)

@pytest.mark.asyncio
async def test_calculate_tag_match_score():
    score = calculate_tag_match_score(["history", "nature"], ["history", "culture", "nature"])
    assert score == 2 / 3

    score = calculate_tag_match_score([], ["history"])
    assert score == 0.0

@pytest.mark.asyncio
async def test_calculate_total_score_for_package_no_places():
    mock_location_repo = AsyncMock()
    score = await calculate_total_score_for_package(
        package={"places": []},
        related_tags=["nature"],
        embeded_description=[0.1, 0.2],
        location_repo=mock_location_repo,
    )
    assert score == 0.0

@pytest.mark.asyncio
async def test_calculate_total_score_for_package_success():
    mock_location_repo = MagicMock()
    # Mock the chaining: location_repo.collection.aggregate().to_list()
    mock_aggregate = MagicMock()
    mock_to_list = AsyncMock()
    mock_to_list.return_value = [
        {"_id": ObjectId(), "tags": ["nature", "wildlife"], "emb_score": 0.8},
        {"_id": ObjectId(), "tags": ["history"], "emb_score": 0.5},
    ]
    mock_aggregate.to_list = mock_to_list
    mock_location_repo.collection.aggregate.return_value = mock_aggregate

    package = {
        "places": [str(ObjectId()), str(ObjectId())]
    }
    
    score = await calculate_total_score_for_package(
        package=package,
        related_tags=["nature", "history"],
        embeded_description=[0.1, 0.2, 0.3],
        location_repo=mock_location_repo,
    )
    
    # Place 1: emb=0.8, tags=["nature", "wildlife"] overlaps with ["nature", "history"] -> 1/2 = 0.5. 
    # Place 1 Score = (0.8 * 0.7) + (0.5 * 0.3) = 0.56 + 0.15 = 0.71
    # Place 2: emb=0.5, tags=["history"] overlaps with ["nature", "history"] -> 1/2 = 0.5.
    # Place 2 Score = (0.5 * 0.7) + (0.5 * 0.3) = 0.35 + 0.15 = 0.50
    # Total Score = (0.71 + 0.50) / 2 = 0.605
    assert abs(score - 0.605) < 0.001

@pytest.mark.asyncio
async def test_calculate_total_score_for_package_no_embedding():
    mock_location_repo = AsyncMock()
    mock_get = AsyncMock()
    mock_get.return_value = {"tags": ["history"]}
    mock_location_repo.get = mock_get
    
    package = {
        "places": [str(ObjectId())]
    }
    
    score = await calculate_total_score_for_package(
        package=package,
        related_tags=["nature", "history"],
        embeded_description=[],
        location_repo=mock_location_repo,
    )
    
    # Place 1: tags=["history"] overlaps with ["nature", "history"] -> 1/2 = 0.5. 
    # Since no embedding, score = tag_score * 0.3 = 0.5 * 0.3 = 0.15
    assert abs(score - 0.15) < 0.001

@pytest.mark.asyncio
@patch("app.services.package.package_recommander.embed_text")
@patch("app.services.package.package_recommander.suggest_tags_from_description")
@patch("app.services.package.package_recommander.calculate_total_score_for_package")
async def test_recommanded_packages(
    mock_calc_score, mock_suggest_tags, mock_embed_text
):
    mock_embed_text.return_value = [0.1, 0.2]
    mock_suggest_tags.return_value = ["nature"]
    
    # Mocking PackageRepo returning raw dicts matching mongo format
    mock_repo = AsyncMock()
    mock_repo.filtered_packages.return_value = [
        {"_id": ObjectId(), "name": "Package A"}, # Should pass threshold
        {"_id": ObjectId(), "name": "Package B"}, # Should fail threshold
    ]
    
    # Let mock_calc_score return THRESHOLD_VALUE + 0.1 for first, and THRESHOLD_VALUE - 0.1 for second
    mock_calc_score.side_effect = [THRESHOLD_VALUE + 0.1, THRESHOLD_VALUE - 0.1]
    
    mock_location_repo = AsyncMock()
    mock_location_repo.get_all_tags = AsyncMock(return_value=["nature", "history"])
    
    results = await recommanded_packages(
        repo=mock_repo,
        location_repo=mock_location_repo,
        min_price=10.0,
        max_price=100.0,
        description="A great nature trip",
        participant_count=2,
        limit=10,
    )
    
    # Expect only one package to be returned since the other is below threshold
    assert len(results) == 1
    assert results[0]["score"] == THRESHOLD_VALUE + 0.1
    # Should be sorted, we only have one so it handles itself
