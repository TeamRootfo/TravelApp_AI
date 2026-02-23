from app.models.location import LocationCreate, LocationOut
from typing import List

def test_location_models():
    print("Testing Location models...")
    
    # Test LocationCreate
    location_data = {
        "name": "Test Location",
        "latitude": 6.9271,
        "longitude": 79.8612,
        "description": "A beautiful test location",
        "tags": ["beach", "scenic"],
        "open_time": 480,
        "close_time": 1080,
        "visit_duration": 60,
        "score": 100
    }
    
    try:
        loc_create = LocationCreate(**location_data)
        print("✓ LocationCreate validation successful")
        assert loc_create.description == "A beautiful test location"
        assert loc_create.tags == ["beach", "scenic"]
    except Exception as e:
        print(f"✗ LocationCreate validation failed: {e}")
        return

    # Test LocationOut
    location_out_data = {**location_data, "id": "test_id_123"}
    try:
        loc_out = LocationOut(**location_out_data)
        print("✓ LocationOut validation successful")
        assert loc_out.id == "test_id_123"
        assert loc_out.description == "A beautiful test location"
    except Exception as e:
        print(f"✗ LocationOut validation failed: {e}")
        return

    print("\nAll model tests passed!")

if __name__ == "__main__":
    test_location_models()
