import os
import secrets

SURVEY_FLOW_VERSION = 'V3.3'
HOUSING_DESIGN_VERSION = 'V2.4'
APP_SEQUENCE = ['eligibility', 'random_matrix', 'household', 'attitudes']
SESSION_CONFIGS = [
    dict(
        name='nuclear_survey_pilot',
        display_name='Power Plant Proximity & Housing Preferences Survey — synthetic Pilot',
        num_demo_participants=1,
        app_sequence=APP_SEQUENCE.copy(),
        study_mode='pilot',
        data_class='synthetic',
        matrix_version='V2.4',
        survey_version='V2.4',
        treatment_design_version='V2.4',
        attitudes_version='V3.3',
        survey_flow_version=SURVEY_FLOW_VERSION,
        housing_design_version=HOUSING_DESIGN_VERSION,
    ),
    dict(
        name='nuclear_survey_live',
        display_name='Power Plant Proximity & Housing Preferences Survey — LIVE DISABLED',
        num_demo_participants=1,
        app_sequence=APP_SEQUENCE.copy(),
        study_mode='live',
        data_class='live',
        matrix_version='TBD',
    ),
]
SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1.0, participation_fee=0.0, doc='V2.4 housing design; synthetic Pilot only'
)
PARTICIPANT_FIELDS = [
    'eligible', 'exit_reason', 'household_complete', 'demo_assignment', 'finished',
    'cookies_allowed',
]
SESSION_FIELDS = []
LANGUAGE_CODE = 'en'
REAL_WORLD_CURRENCY_CODE = 'SEK'
USE_POINTS = False
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = os.environ.get('OTREE_ADMIN_PASSWORD')
# Ephemeral local fallback; deployment requires an externally supplied stable secret.
SECRET_KEY = os.environ.get('OTREE_SECRET_KEY') or secrets.token_hex(32)
INSTALLED_APPS = ['otree']
