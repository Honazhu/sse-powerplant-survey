from otree.api import Bot, Submission, SubmissionMustFail
from . import Introduction, VoluntaryParticipation, AgeConfirmation, Exit


class PlayerBot(Bot):
    cases = ['adult', 'under_18', 'declined', 'adult_no_cookies', 'adult_cookies_blocked',
             'adult_age46', 'adult_age56', 'adult_age66']

    def play_round(self):
        qualifies = self.case.startswith('adult')
        assert self.participant.code
        assert self.session.config['app_sequence'] == ['eligibility', 'random_matrix', 'household', 'attitudes']
        assert 'Q1a.' in self.html
        assert 'id="survey-reference-code"' not in self.html
        yield SubmissionMustFail(AgeConfirmation, dict(adult_confirmed=''), error_fields=['adult_confirmed'])
        yield AgeConfirmation, dict(adult_confirmed=self.case != 'under_18')
        assert self.participant.eligible is False  # No consent yet.
        if self.case != 'under_18':
            assert 'Welcome to the survey' in self.html
            yield Introduction
            assert 'Privacy &amp; Data Use' in self.html
            assert '43086@student.hhs.se' in self.html
            assert 'cookie-probe-status' in self.html
            assert 'id="survey-reference-code"' not in self.html
            if self.case == 'declined':
                # Refusal must work without any cookie preference.
                yield VoluntaryParticipation, dict(willing_to_participate=False, cookie_probe_status='not_tested')
            else:
                yield SubmissionMustFail(VoluntaryParticipation, dict(willing_to_participate=True,
                    cookie_probe_status='not_tested'), error_fields=['cookies_allowed'])
                allowed = self.case != 'adult_no_cookies'
                status = 'blocked' if self.case == 'adult_cookies_blocked' else 'supported'
                yield VoluntaryParticipation, dict(willing_to_participate=True,
                    cookies_allowed=allowed, cookie_probe_status=status if allowed else 'declined')
                assert self.participant.cookies_allowed == allowed
                assert self.player.cookie_probe_status == (status if allowed else 'declined')
                assert 'id="survey-reference-code"' in self.html
        assert self.participant.eligible == qualifies
        if not qualifies:
            assert 'Thank you for your interest!' in self.html
            assert 'id="survey-reference-code"' not in self.html
            assert 'otree-btn-next' not in self.html
            if self.case == 'under_18':
                assert 'open only to participants aged 18 or above' in self.html
                assert self.player.field_maybe_none('willing_to_participate') is None
            assert self.player.field_maybe_none('cookies_allowed') is None
            yield Submission(Exit, check_html=False)
            assert 'Household information' not in self.html
            assert 'Housing scenario' not in self.html
