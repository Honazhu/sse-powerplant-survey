/* UI enhancement only. Python validates and saves every answer. No storage/network. */
(() => {
    const root = document.querySelector('[data-household-questions]');
    if (!root) return;
    const rent = root.querySelector('[name="monthly_rent_sek"]');
    const income = root.querySelector('[name="income_thousand_sek"]');
    const refusal = root.querySelector('[name="income_not_disclosed"]');
    const form = root.closest('form');
    const error = 'Please enter a valid number.';
    function showError(field, message) {
        document.getElementById(field.name + '-errors').textContent = message;
        field.setAttribute('aria-invalid', message ? 'true' : 'false');
        field.setCustomValidity(message);
    }
    function validate(field) {
        if (field.disabled) { showError(field, ''); return true; }
        const valid = /^[0-9]+$/.test(field.value) &&
            BigInt(field.value) >= BigInt(field.dataset.minimum) &&
            BigInt(field.value) <= (field === income ? 9223372036854775n : 9223372036854775807n);
        showError(field, valid ? '' : error);
        return valid;
    }
    function conditions() {
        const choice = root.querySelector('[name="rent_status"]:checked');
        const paysRent = choice && choice.value === 'True';
        document.getElementById('rent-amount').hidden = !paysRent;
        rent.disabled = !paysRent;
        rent.required = !!paysRent;
        income.disabled = refusal.checked;
        income.required = !refusal.checked;
        for (const field of [rent, income]) {
            if (field.disabled) { field.value = ''; showError(field, ''); }
        }
    }
    root.querySelectorAll('[name="rent_status"], [name="income_not_disclosed"]').forEach(field => field.addEventListener('change', conditions));
    for (const field of [rent, income]) {
        field.addEventListener('input', () => validate(field));
        field.addEventListener('blur', () => validate(field));
        field.addEventListener('invalid', () => validate(field));
    }
    // Capture before framework submit listeners. Native navigation remains intact.
    form.addEventListener('submit', event => {
        const results = [validate(rent), validate(income)];
        if (results.includes(false)) {
            event.preventDefault();
            event.stopImmediatePropagation();
            [rent, income][results.indexOf(false)].focus();
        }
    }, true);
    conditions();
})();
