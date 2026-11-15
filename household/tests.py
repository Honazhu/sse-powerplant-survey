from otree.api import Bot, SubmissionMustFail
from . import HouseholdInformation
from .questions import AGE


class PlayerBot(Bot):
    cases = [0, None, None, 1, 2, 3, 4, 5]

    def play_round(self):
        if not self.participant.eligible:
            assert not self.participant.household_complete
            assert not self.player.placeholder_completed
            return
        assert self.participant.code in self.html
        assert 'id="survey-reference-code"' in self.html
        values = dict(age_group=AGE['choices'][self.case][0], rent_status=True,
                      monthly_rent_sek=6500, income_thousand_sek=25,
                      income_not_disclosed='', previous_power_plant_exposure=self.case % 3)
        if self.case == 0:
            for field in ['age_group', 'rent_status', 'previous_power_plant_exposure']:
                yield SubmissionMustFail(HouseholdInformation, dict(values, **{field: ''}), error_fields=[field])
            for field in ['monthly_rent_sek', 'income_thousand_sek']:
                for invalid in ['', '   ', 'abc', '-1', '1.5', '1e3', '+2', ' 25', '2_000', '９', str(2**64)]:
                    yield SubmissionMustFail(HouseholdInformation, dict(values, **{field: invalid}), error_fields=[field])
                    assert 'Please enter a valid number.' in self.html
            yield SubmissionMustFail(HouseholdInformation, dict(values, monthly_rent_sek=0), error_fields=['monthly_rent_sek'])
            for field, invalid in [('age_group', 'under_18'), ('previous_power_plant_exposure', 3)]:
                yield SubmissionMustFail(HouseholdInformation, dict(values, **{field: invalid}), error_fields=[field])
        if self.case == 1:
            values.update(rent_status=False, monthly_rent_sek=12345, income_thousand_sek=0)
        if self.case == 2:
            values.update(rent_status=False, monthly_rent_sek='stale-invalid',
                          income_not_disclosed=True, income_thousand_sek='stale-invalid')
        if self.case == 3:
            values.update(rent_status=False)
            values.pop('monthly_rent_sek')
        if self.case == 4:
            values.update(income_not_disclosed=True)
            values.pop('income_thousand_sek')
        yield HouseholdInformation, values
        assert self.participant.household_complete is True
        assert self.player.age_group == values['age_group']
        assert self.player.previous_power_plant_exposure == self.case % 3
        assert self.player.field_maybe_none('monthly_rent_sek') == (6500 if values['rent_status'] else None)
        expected = None if values['income_not_disclosed'] else values['income_thousand_sek']
        assert self.player.field_maybe_none('income_thousand_sek') == expected
        assert self.player.field_maybe_none('income_sek') == (None if expected is None else expected * 1000)
        assert self.participant.code in self.html
