"""Research-locked V2.0 design. N/F are profiles, never display positions."""
from collections import Counter
import hashlib
import json

DESIGN_VERSION = 'V2.0'
SIZE_LEVELS = (40, 55, 70)
DISTANCE_LEVELS = (10, 30)
BASELINE_RENT = {40: 6000, 55: 7500, 70: 9000}
RENT_OFFSETS = (-1000, -500, 0, 500, 1000)
# set_id, block_id, N size, N rent, F size, F rent (SEK/month)
CHOICE_SETS = (
    ('S01', 1, 40, 6000, 40, 6500),
    ('S02', 1, 70, 8500, 70, 9500),
    ('S03', 1, 40, 6000, 55, 7500),
    ('S04', 1, 55, 7000, 40, 6500),
    ('S05', 2, 55, 7000, 55, 8500),
    ('S06', 2, 70, 8000, 70, 10000),
    ('S07', 2, 40, 5000, 55, 7500),
    ('S08', 2, 55, 7000, 40, 7000),
    ('S09', 3, 40, 6000, 40, 6000),
    ('S10', 3, 70, 9000, 70, 9500),
    ('S11', 3, 55, 8500, 70, 9000),
    ('S12', 3, 70, 9500, 55, 8000),
)
PROFILE_FIELDS = ('size_m2', 'distance_km', 'rent_sek_month', 'near20', 'facility_type')


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def profile(size, rent, distance):
    return dict(size_m2=size, rent_sek_month=rent, distance_km=distance,
                near20=int(distance < 20), facility_type='nuclear')


def design_payload():
    return dict(design_version=DESIGN_VERSION, choice_sets=[
        dict(choice_set_id=sid, block_id=block, N=profile(ns, nr, 10), F=profile(fs, fr, 30))
        for sid, block, ns, nr, fs, fr in CHOICE_SETS
    ])


DESIGN_HASH = hashlib.sha256(canonical_json(design_payload()).encode('utf-8')).hexdigest()


def validate_design():
    assert len(CHOICE_SETS) == len({r[0] for r in CHOICE_SETS}) == 12
    assert Counter(r[1] for r in CHOICE_SETS) == {1: 4, 2: 4, 3: 4}
    for _, _, ns, nr, fs, fr in CHOICE_SETS:
        assert abs(ns - fs) <= 15
        for size, rent in ((ns, nr), (fs, fr)):
            assert size in SIZE_LEVELS and rent - BASELINE_RENT[size] in RENT_OFFSETS
    for block in (1, 2, 3):
        signs = Counter((r[2] > r[4]) - (r[2] < r[4]) for r in CHOICE_SETS if r[1] == block)
        assert signs == {0: 2, -1: 1, 1: 1}


validate_design()
