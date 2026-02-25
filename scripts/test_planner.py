from app.services.planner.multi_day import plan_trip_multi_day_carry_end_forward


def main():
    locations = [
        {
            "name": "Start",
            "latitude": 6.9271,
            "longitude": 79.8612,
            "open_time": 0,
            "close_time": 1440,
            "visit_duration": 0,
            "score": 0,
        },
        {
            "name": "Temple A",
            "latitude": 6.9200,
            "longitude": 79.8700,
            "open_time": 540,
            "close_time": 1020,
            "visit_duration": 60,
            "score": 100,
        },
        {
            "name": "Museum B",
            "latitude": 6.9100,
            "longitude": 79.8800,
            "open_time": 600,
            "close_time": 1200,
            "visit_duration": 45,
            "score": 80,
        },
        {
            "name": "National Library",
            "latitude": 6.9210,
            "longitude": 79.8670,
            "open_time": 540,
            "close_time": 1080,
            "visit_duration": 30,
            "score": 70,
        },
        {
            "name": "Galle Face Green",
            "latitude": 6.9270,
            "longitude": 79.8428,
            "open_time": 0,
            "close_time": 1440,
            "visit_duration": 30,
            "score": 60,
        },
        {
            "name": "Independence Square",
            "latitude": 6.9036,
            "longitude": 79.8693,
            "open_time": 480,
            "close_time": 1080,
            "visit_duration": 40,
            "score": 75,
        },
        {
            "name": "Old Parliament",
            "latitude": 6.9335,
            "longitude": 79.8486,
            "open_time": 540,
            "close_time": 1020,
            "visit_duration": 35,
            "score": 65,
        },
        {
            "name": "Beira Lake",
            "latitude": 6.9279,
            "longitude": 79.8559,
            "open_time": 480,
            "close_time": 1200,
            "visit_duration": 50,
            "score": 85,
        },
        {
            "name": "Pettah Market",
            "latitude": 6.9352,
            "longitude": 79.8501,
            "open_time": 480,
            "close_time": 1140,
            "visit_duration": 45,
            "score": 90,
        },
        {
            "name": "Kelaniya Temple",
            "latitude": 6.9490,
            "longitude": 79.9187,
            "open_time": 480,
            "close_time": 1080,
            "visit_duration": 60,
            "score": 95,
        },
        {
            "name": "Negombo Beach",
            "latitude": 7.2086,
            "longitude": 79.8358,
            "open_time": 480,
            "close_time": 1200,
            "visit_duration": 90,
            "score": 90,
        },
        {
            "name": "Gangaramaya Temple",
            "latitude": 6.9167,
            "longitude": 79.8562,
            "open_time": 540,
            "close_time": 1080,
            "visit_duration": 50,
            "score": 85,
        },
        {
            "name": "End",
            "latitude": 7.2080,
            "longitude": 79.8350,
            "open_time": 0,
            "close_time": 1440,
            "visit_duration": 0,
            "score": 0,
        },
    ]

    res = plan_trip_multi_day_carry_end_forward(
        all_locations=locations,
        start_original_index=0,
        end_original_index=2,
        start_time_minutes=8 * 60,
        trip_days=2,
        daily_time_budget_minutes=600,
        max_stops_per_day=3,
    )
    print(res)


if __name__ == "__main__":
    main()
