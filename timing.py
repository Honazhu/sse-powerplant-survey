"""Page elapsed-time export using native oTree completion events.

V1 can map one-question pages to question IDs. This is wall-clock elapsed time,
including network delay and time away from the tab, not active attention time.
"""
import csv
from io import StringIO

TIMING_VERSION = 'page-completion-delta-v1'
EXPORT_FIELDS = [
    'session_code', 'participant_code', 'page_index', 'app_name', 'page_name',
    'round_number', 'epoch_time_completed', 'timeout_happened', 'is_wait_page',
    'seconds_on_page', 'timing_status', 'timing_version',
]


def iter_page_durations(rows):
    """Derive intervals in native event order, isolated by session/participant.

    InitializeParticipant supplies the first baseline. Missing or backwards
    timestamps produce a missing duration, never an invented zero.
    """
    previous = {}
    for row in rows:
        key = (row['session_code'], row['participant_code'])
        timestamp = int(row['epoch_time_completed'])
        baseline = previous.get(key)
        previous[key] = timestamp
        if row['page_name'] == 'InitializeParticipant':
            continue
        result = {name: row[name] for name in EXPORT_FIELDS[:9]}
        if baseline is None:
            duration, status = '', 'missing_baseline'
        elif timestamp < baseline:
            duration, status = '', 'clock_reversed'
        else:
            duration, status = timestamp - baseline, 'ok'
        result.update(
            seconds_on_page=duration, timing_status=status, timing_version=TIMING_VERSION
        )
        yield result


def export_page_durations(players):
    """oTree custom_export adapter; filters native events to selected players."""
    from otree.export import export_page_times

    allowed = {(p.session.code, p.participant.code) for p in players}
    buffer = StringIO()
    export_page_times(buffer)
    buffer.seek(0)
    rows = (
        row for row in csv.DictReader(buffer)
        if (row['session_code'], row['participant_code']) in allowed
    )
    yield EXPORT_FIELDS
    for row in iter_page_durations(rows):
        yield [row[field] for field in EXPORT_FIELDS]
