/* Progressive enhancement: native radios are the only named/submitted controls.
   The unnamed range is never an answer until deliberate input. No storage/autosave. */
'use strict';
for (const question of document.querySelectorAll('.survey-attitude-question')) {
    const fallback = question.querySelector('[data-radio-fallback]');
    const radios = Array.from(fallback.querySelectorAll('input[type="radio"]'));
    const slider = question.querySelector('[data-slider]');
    const range = slider.querySelector('input[type="range"]');
    if (range.type !== 'range') continue;
    const status = slider.querySelector('[role="status"]');
    const hint = slider.querySelector('[data-slider-hint]');
    const error = slider.querySelector('[data-slider-error]');
    const labels = Array.from(slider.querySelectorAll('[data-score]'));
    // Only server-rendered checked states survive an error response. Fresh GETs
    // safely require answers again, even if the browser restores form controls.
    for (const radio of radios) {
        radio.checked = radio.defaultChecked;
        radio.required = false;
    }
    const refresh = () => {
        const selected = radios.find(radio => radio.checked);
        const answered = Boolean(selected);
        slider.dataset.answered = String(answered);
        range.value = answered ? selected.value : '0';
        const label = answered ? labels.find(item => item.dataset.score === selected.value).textContent : 'Not answered';
        status.textContent = answered ? 'Selected: ' + label : 'Not answered';
        hint.hidden = answered;
        range.setAttribute('aria-valuetext', label);
        range.setCustomValidity(answered ? '' : 'Please choose a response for this statement.');
        range.setAttribute('aria-invalid', String(!answered && !error.hidden));
        for (const item of labels) {
            const active = answered && item.dataset.score === selected.value;
            item.classList.toggle('is-selected', active);
            item.setAttribute('aria-pressed', String(active));
        }
    };
    const select = () => {
        const radio = radios.find(item => item.value === range.value);
        if (!radio) return;
        radio.checked = true;
        error.hidden = true;
        question.querySelector('.survey-field-errors').hidden = true;
        if (!Array.from(document.querySelectorAll('.survey-attitude-question .form-control-errors')).some(item => !item.closest('[hidden]'))) {
            const summary = document.querySelector('.otree-form-errors');
            if (summary) summary.hidden = true;
        }
        refresh();
    };
    range.addEventListener('input', select);
    // These buttons have no name and never submit. Reuse the same single-radio
    // update as dragging, including an explicit selection of Neutral (0).
    for (const item of labels) {
        item.addEventListener('click', () => {
            range.value = item.dataset.score;
            select();
        });
    }
    // A tap on the central position or an endpoint key at its boundary may not
    // emit input; these deliberate actions must still allow Neutral/endpoints.
    range.addEventListener('pointerup', select);
    range.addEventListener('keyup', event => {
        if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home', 'End', 'PageUp', 'PageDown'].includes(event.key)) select();
    });
    range.addEventListener('invalid', () => {
        error.hidden = false;
        range.setAttribute('aria-invalid', 'true');
    });
    refresh();
    range.disabled = false;
    slider.hidden = false;
    fallback.hidden = true;
}
