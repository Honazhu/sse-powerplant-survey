"""Native bots exercise each required choice and actual repeated HTTP GETs."""
import json
from otree.api import Bot, SubmissionMustFail
from . import Choice, ScenarioInstructions
from .randomization import assign_once, displayed_task


class PlayerBot(Bot):
    def play_round(self):
        assert self.player.wording_version == 'V2.4'
        if not self.participant.eligible:
            assert not self.player.task_displayed
            assert not self.player.in_round(1).module_started
            assert self.player.field_maybe_none('choice') is None
            return
        assert not self.participant.household_complete
        if self.round_number == 1:
            assert 'id="rental-scenario"' in self.html
            assert 'These are hypothetical housing scenarios' in self.html
            assert 'id="power-plant-context"' not in self.html
            assert 'Continue to Housing Choices' in self.html
            assert self.player.field_maybe_none('assignment_json') is None
            assert self.player.field_maybe_none('task_started_at') is None
            yield ScenarioInstructions
        before = self.player.in_round(1).assignment_json
        assignment = json.loads(before)
        task = displayed_task(self.player)
        assert f'Choice {self.round_number} of 4' in self.html
        assert task['choice_set_id'] in self.html
        label = {'nuclear': 'Nuclear', 'oil_fired': 'Oil-fired'}[task['facility_type']]
        assert f'Power plant context: {label} power plant' in self.html
        assert task['A']['facility_type'] == task['B']['facility_type'] == self.player.facility_type
        assert 'data-wording-version="V2.4"' in self.html
        assert 'id="rental-scenario"' not in self.html
        assert 'id="budget-reminder"' not in self.html
        assert 'id="repeated-task-reminder"' not in self.html
        for side in ('A', 'B'):
            assert f"{task[side]['rent_sek_month']:,}" in self.html
        assert self.player.field_maybe_none('choice') is None
        assert 'checked' not in self.html.split('<fieldset')[1].split('</fieldset>')[0]
        started = self.player.task_started_at
        for _ in range(2):
            response = self.participant_bot.client.get(self.participant_bot.url)
            assert response.status_code == 200
            assert task['choice_set_id'] in response.text
            assert self.player.in_round(1).assignment_json == before
            assert self.player.task_started_at == started
        assert assign_once(self.player) == assignment
        for invalid in ('', 'C', 'Near'):
            yield SubmissionMustFail(Choice, dict(choice=invalid), error_fields=['choice'])
        choice = 'A' if self.round_number % 2 else 'B'
        yield Choice, dict(choice=choice)
        assert self.player.choice == choice
        assert self.player.chosen_near20 == task[choice]['near20']
        assert self.player.task_duration_s >= 0
        assert self.player.in_round(1).tasks_answered == self.round_number
        assert self.player.in_round(1).module_completed == (self.round_number == 4)
