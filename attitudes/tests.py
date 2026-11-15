from otree.api import Bot, SubmissionMustFail
from . import AttitudeSurvey
from .questions import RAW_FIELDS


class PlayerBot(Bot):
    cases = [0, None, None, 2, -2, 0, -1, 1]

    def play_round(self):
        if self.participant.eligible:
            assert self.participant.household_complete is True
            assert self.player.attitudes_version == 'V3.3'
            assert 'Submit and Continue' in self.html
            assert 'checked' not in self.html.split('data-attitudes-version=')[1].split('</fieldset>')[0]
            values = {field: self.case if self.case != 99 else 0 for field in RAW_FIELDS}
            if self.case == 0:
                for field in RAW_FIELDS:
                    yield SubmissionMustFail(AttitudeSurvey, dict(values, **{field: ''}), error_fields=[field])
                    for invalid in (3, 99, '0.5', 'bad'):
                        yield SubmissionMustFail(AttitudeSurvey, dict(values, **{field: invalid}), error_fields=[field])
                yield SubmissionMustFail(AttitudeSurvey, dict(values, nuclear_support=99), error_fields=['nuclear_support'])
                assert all(self.player.field_maybe_none(field) is None for field in RAW_FIELDS)
            yield AttitudeSurvey, values
            assert all(getattr(self.player, field) == value for field, value in values.items())
            assert self.player.attitudes_completed is True
            assert self.player.completed is True
            assert self.participant.finished is True
            assert 'Completion' in self.html
            assert 'Your responses have been saved' in self.html
        else:
            assert self.player.completed is False
            assert self.participant.finished is False
            assert self.player.attitudes_completed is False
