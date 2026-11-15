"""Lossless native-to-attitude-wide conversion; no database or oTree imports."""
import math
from .questions import ATTITUDES_VERSION, QUESTIONS, RAW_FIELDS, SCORE_FIELDS, DK_FIELDS
from .validation import score_response
from .legacy_questions_v30 import QUESTIONS as V30_QUESTIONS

VERSION_QUESTIONS = {'V3.0': V30_QUESTIONS, ATTITUDES_VERSION: QUESTIONS}

KEYS = ['session_code', 'participant_code']
META_FIELDS = ['study_mode', 'data_class', 'attitudes_version', 'attitudes_completed',
               'attitudes_submitted_at', 'attitudes_status']
EXPORT_FIELDS = KEYS + META_FIELDS + RAW_FIELDS + SCORE_FIELDS + DK_FIELDS
NATIVE_FIELDS = ['attitudes_version', 'attitudes_completed', 'attitudes_submitted_at'] + RAW_FIELDS


def text_value(value):
    if value is None:
        return ''
    if isinstance(value, bool):
        return str(int(value))
    return str(value)


def participant_key(row):
    values = tuple(row[name] for name in KEYS)
    if any(not isinstance(value, str) or not value or value.strip() != value for value in values):
        raise ValueError('Join keys must be nonempty, unmodified strings.')
    return values


def scored_record(source):
    """Validate raw response provenance before deriving scores/DK/status."""
    row = {name: text_value(source.get(name)) for name in EXPORT_FIELDS}
    participant_key(row)
    version = row['attitudes_version']
    if version and version not in VERSION_QUESTIONS:
        raise ValueError('Unsupported attitudes version; no automatic relabelling.')
    if not version:
        if any(row[name] for name in NATIVE_FIELDS):
            raise ValueError('Unversioned attitude response or completion metadata.')
        row['attitudes_status'] = 'historical_unavailable'
    else:
        completed = row['attitudes_completed']
        if completed not in ('0', '1'):
            raise ValueError('Current attitudes require an explicit completion status.')
        if completed == '0':
            if row['attitudes_submitted_at'] or any(row[name] for name in RAW_FIELDS):
                raise ValueError('Unsubmitted attitudes must not contain formal responses.')
            row['attitudes_status'] = 'not_submitted'
        else:
            try:
                submitted = float(row['attitudes_submitted_at'])
            except ValueError as error:
                raise ValueError('Completed attitudes require a submission timestamp.') from error
            if not math.isfinite(submitted) or submitted <= 0:
                raise ValueError('Invalid attitude submission timestamp.')
            row['attitudes_status'] = 'submitted'
    for question in VERSION_QUESTIONS.get(version, QUESTIONS):
        raw = row[question['field']]
        if raw == '':
            if row['attitudes_completed'] == '1':
                raise ValueError('Completed attitudes must contain all five responses.')
            value = None
        else:
            allowed = {str(code) for code, _ in question['choices']}
            if raw not in allowed:
                raise ValueError(f"Invalid raw attitude code: {question['field']}.")
            value = int(raw)
        score, dk = score_response(value, question)
        row[question['score_field']] = text_value(score)
        if question['dk_field']:
            row[question['dk_field']] = text_value(dk)
    return row


def validate_wide(rows):
    """Reject duplicate keys and derived scores/status inconsistent with raw data."""
    output, seen = [], set()
    for source in rows:
        if set(source) != set(EXPORT_FIELDS):
            raise ValueError('Attitudes wide columns do not match the supported schema.')
        row = {name: text_value(source[name]) for name in EXPORT_FIELDS}
        key = participant_key(row)
        if key in seen:
            raise ValueError('Duplicate attitudes participant/session key.')
        seen.add(key)
        expected = scored_record(row)
        if row != expected:
            raise ValueError('Attitude scores, DK indicators or status disagree with raw answers.')
        output.append(row)
    return output


def records_from_native(rows):
    output = []
    prefix = 'attitudes.1.player.'
    for source in rows:
        session_version = source.get('session.config.attitudes_version', '')
        if session_version and (session_version not in VERSION_QUESTIONS or source.get(prefix + 'attitudes_version') != session_version):
            raise ValueError('Current session is missing its attitude version; no historical fallback.')
        if source.get(prefix + 'attitudes_version') in VERSION_QUESTIONS:
            if any(prefix + name not in source for name in NATIVE_FIELDS):
                raise ValueError('Current native export lacks attitude columns.')
        row = {name: source.get(prefix + name, '') for name in NATIVE_FIELDS}
        row.update(session_code=source['session.code'], participant_code=source['participant.code'],
                   study_mode=source['session.config.study_mode'], data_class=source['session.config.data_class'])
        row = scored_record(row)
        if row['attitudes_completed'] == '1':
            if any(source.get(name) != '1' for name in (
                    'participant.eligible', 'participant.household_complete', 'participant.finished',
                    'random_matrix.1.player.module_completed', prefix + 'completed')):
                raise ValueError('Submitted attitudes conflict with upstream/survey completion.')
        output.append(row)
    return validate_wide(output)
