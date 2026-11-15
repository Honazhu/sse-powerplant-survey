/* No cookie access until the user explicitly selects Allow. */
(function () {
    'use strict';
    const status = document.getElementById('cookie-probe-status');
    const message = document.getElementById('cookie-probe-message');
    const choices = document.querySelectorAll('input[name="cookies_allowed"]');
    function update() {
        const selected = document.querySelector('input[name="cookies_allowed"]:checked');
        if (!selected) return;
        if (selected.value !== 'True' && selected.value !== 'true' && selected.value !== '1') {
            status.value = 'declined';
            message.textContent = 'No cookie test will run. You may continue.';
            return;
        }
        let supported = false;
        const suffix = '; Path=/; SameSite=Lax' + (location.protocol === 'https:' ? '; Secure' : '');
        try {
            document.cookie = 'nuclear_cookie_probe=1' + suffix;
            supported = document.cookie.split(';').some(
                item => item.trim() === 'nuclear_cookie_probe=1'
            );
        } catch (_) {
            supported = false;
        } finally {
            try { document.cookie = 'nuclear_cookie_probe=; Max-Age=0' + suffix; }
            catch (_) { /* Cookies may be disabled by the browser. */ }
        }
        status.value = supported ? 'supported' : 'blocked';
        message.textContent = supported
            ? 'Temporary cookie worked and was removed. You may continue.'
            : 'Cookie test was blocked. You may still continue using your participant link.';
    }
    choices.forEach(choice => choice.addEventListener('change', update));
    // Submission handles a retained selection after validation without probing on load.
    status.closest('form').addEventListener('submit', update);
}());
