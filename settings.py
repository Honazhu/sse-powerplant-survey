import os
import secrets

APP_SEQUENCE = ['eligibility', 'random_matrix', 'attitudes', 'household']
SURVEY_FLOW_VERSION = 'final'
HOUSING_DESIGN_VERSION = 'V2.4'
SESSION_CONFIGS = [
    dict(name='survey_final_production', display_name='Housing preferences — Final production', num_demo_participants=1,
         app_sequence=APP_SEQUENCE.copy(), study_mode='live', data_class='production', matrix_version='V2.4',
         survey_version='final', survey_flow_version='final', treatment_design_version='V5.0', attitudes_version='final'),
    dict(name='survey_final_qa', display_name='Housing preferences — isolated QA', num_demo_participants=20,
         app_sequence=APP_SEQUENCE.copy(), study_mode='qa', data_class='synthetic', matrix_version='V2.4',
         survey_version='final', survey_flow_version='final', treatment_design_version='V5.0', attitudes_version='final'),
]
SESSION_CONFIG_DEFAULTS = dict(real_world_currency_per_point=1.0, participation_fee=0.0, doc='Final housing survey')
PARTICIPANT_FIELDS = ['eligible', 'exit_reason', 'household_complete', 'demo_assignment', 'finished', 'cookies_allowed', 'show_reference']
SESSION_FIELDS = []
LANGUAGE_CODE = 'en'
REAL_WORLD_CURRENCY_CODE = 'SEK'
USE_POINTS = False
ADMIN_USERNAME = 'admin'
if os.environ.get('OTREE_PRODUCTION') not in (None, '', '0'):
    if not os.environ.get('OTREE_SECRET_KEY') or not os.environ.get('OTREE_ADMIN_PASSWORD'):
        raise RuntimeError('Production requires OTREE_SECRET_KEY and OTREE_ADMIN_PASSWORD.')
    if not os.environ.get('DATABASE_URL', '').startswith(('postgres://', 'postgresql://')):
        raise RuntimeError('Production requires an isolated PostgreSQL DATABASE_URL.')
ADMIN_PASSWORD = os.environ.get('OTREE_ADMIN_PASSWORD')
SECRET_KEY = os.environ.get('OTREE_SECRET_KEY') or secrets.token_hex(32)
INSTALLED_APPS = ['otree']
