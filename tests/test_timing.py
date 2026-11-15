from timing import iter_page_durations


def event(code, page, timestamp):
    return dict(
        session_code='synthetic-session', participant_code=code,
        page_index='1', app_name='eligibility', page_name=page, round_number='1',
        epoch_time_completed=str(timestamp), timeout_happened='0', is_wait_page='0',
    )


def test_elapsed_times_use_separate_participant_baselines():
    rows = [
        event('synthetic-A', 'InitializeParticipant', 100),
        event('synthetic-B', 'InitializeParticipant', 101),
        event('synthetic-A', 'Question1', 112),
        event('synthetic-B', 'Question1', 105),
        event('synthetic-A', 'Question2', 130),
    ]
    assert [r['seconds_on_page'] for r in iter_page_durations(rows)] == [12, 4, 18]


def test_missing_and_reversed_timestamps_are_not_zero():
    rows = [event('synthetic-A', 'Question1', 100), event('synthetic-A', 'Question2', 99)]
    results = list(iter_page_durations(rows))
    assert [r['seconds_on_page'] for r in results] == ['', '']
    assert [r['timing_status'] for r in results] == ['missing_baseline', 'clock_reversed']
