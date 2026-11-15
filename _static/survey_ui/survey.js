/* Shared presentation and explicit local clipboard action; no tracking or network calls. */
document.documentElement.lang = 'en';
const surveyViewport = document.querySelector('meta[name="viewport"]');
if (surveyViewport) surveyViewport.content = 'width=device-width, initial-scale=1.0, viewport-fit=cover';
document.querySelectorAll('.survey-next .otree-btn-next').forEach(button => {
    button.textContent = button.dataset.continueLabel || 'Continue';
    button.type = 'submit';
});

const copyReference = document.querySelector('[data-copy-reference]');
if (copyReference) copyReference.addEventListener('click', async () => {
    const code = document.querySelector('#survey-reference-code');
    const status = document.querySelector('[data-copy-status]');
    try {
        if (!navigator.clipboard) throw new Error('Clipboard unavailable');
        await navigator.clipboard.writeText(code.textContent.trim());
        status.textContent = 'Copied';
    } catch (_) {
        const selection = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(code);
        selection.removeAllRanges();
        selection.addRange(range);
        status.textContent = 'Please copy the selected ID manually.';
    }
});
