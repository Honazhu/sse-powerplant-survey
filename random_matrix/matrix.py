"""Frozen V2.4 homes. Canonical A/B orientation is part of the design hash."""
from collections import Counter
import hashlib
import json

DESIGN_VERSION = 'V2.4'
BASE_RENT_SEK = 6500
DISTANCE_LEVELS = (10, 50)
PREMIUM_LEVELS = (0, 500, 1000, 2000)
BLOCKS = {'A': ('S01', 'S04', 'S06', 'S07'), 'B': ('S02', 'S03', 'S05', 'S08')}
# ID, facility, canonical A distance/rent, canonical B distance/rent.
CHOICE_SETS = (
    ('S01', 'nuclear',   10, 6500, 50, 7500),
    ('S02', 'oil_fired', 50, 7000, 10, 6500),
    ('S03', 'nuclear',   50, 8500, 10, 6500),
    ('S04', 'oil_fired', 10, 6500, 50, 8500),
    ('S05', 'nuclear',   10, 6500, 50, 6500),
    ('S06', 'oil_fired', 50, 6500, 10, 6500),
    ('S07', 'nuclear',   50, 7000, 10, 6500),
    ('S08', 'oil_fired', 10, 6500, 50, 7500),
)
PROFILE_FIELDS = ('distance_km', 'rent_sek_month', 'near20', 'facility_type')


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def profile(distance, rent, facility):
    return dict(distance_km=distance, rent_sek_month=rent,
                near20=int(distance < 20), facility_type=facility)


def design_payload():
    sets = []
    for sid, facility, ad, ar, bd, br in CHOICE_SETS:
        sets.append(dict(choice_set_id=sid, facility_type=facility,
                         block_id=next(b for b, ids in BLOCKS.items() if sid in ids),
                         base_rent_sek=BASE_RENT_SEK,
                         premium_sek=(ar if ad == 50 else br) - BASE_RENT_SEK,
                         A=profile(ad, ar, facility), B=profile(bd, br, facility)))
    return dict(design_version=DESIGN_VERSION, choice_sets=sets, blocks=BLOCKS,
                distance_levels=DISTANCE_LEVELS, premium_levels=PREMIUM_LEVELS,
                base_rent_sek=BASE_RENT_SEK, housing_size='identical-not-randomized',
                facility_scope='same-plant-task-context',
                allocation_rule='permuted-AB-pairs-atomic-first-eligible-Choice-v1',
                order_rule='participant-seeded-uniform-four-set-shuffle',
                side_rule='independent-facility-coins-one-near-A-one-near-B-per-facility',
                profile_rule='swap-whole-canonical-profiles', demographic_inputs=False)


DESIGN_HASH = hashlib.sha256(canonical_json(design_payload()).encode()).hexdigest()


def validate_design():
    sets = design_payload()['choice_sets']
    assert len(sets) == len({s['choice_set_id'] for s in sets}) == 8
    assert Counter(s['facility_type'] for s in sets) == {'nuclear': 4, 'oil_fired': 4}
    for s in sets:
        assert {s[x]['distance_km'] for x in 'AB'} == {10, 50}
        for x in 'AB':
            p = s[x]
            assert p['near20'] == int(p['distance_km'] < 20)
            assert p['rent_sek_month'] == BASE_RENT_SEK + (s['premium_sek'] if p['distance_km'] == 50 else 0)
            assert p['facility_type'] == s['facility_type']
    for facility in ('nuclear', 'oil_fired'):
        assert sorted(s['premium_sek'] for s in sets if s['facility_type'] == facility) == list(PREMIUM_LEVELS)
    for block, ids in BLOCKS.items():
        selected = [s for s in sets if s['block_id'] == block]
        assert tuple(s['choice_set_id'] for s in selected) == ids
        assert sorted(s['premium_sek'] for s in selected) == list(PREMIUM_LEVELS)
        for facility in ('nuclear', 'oil_fired'):
            assert sorted(s['A']['near20'] for s in selected if s['facility_type'] == facility) == [0, 1]


validate_design()
