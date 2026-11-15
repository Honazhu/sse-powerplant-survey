/* Optional developer check: node tests/test_cookie_probe.js. No npm dependencies. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../_static/cookie_probe.js'), 'utf8');

function run(choice, blocked) {
    let cookie = '', reads = 0;
    const writes = [], handlers = {};
    const form = {addEventListener: (name, fn) => {handlers[name] = fn;}};
    const status = {value: 'not_tested', closest: () => form};
    const message = {};
    const document = {
        getElementById: id => id === 'cookie-probe-status' ? status : message,
        querySelectorAll: () => [{addEventListener: (name, fn) => {handlers[name] = fn;}}],
        querySelector: () => choice === null ? null : {value: choice},
        get cookie() { reads++; return cookie; },
        set cookie(value) {
            writes.push(value);
            if (blocked) throw new Error('Browser blocked cookies');
            cookie = value.includes('Max-Age=0') ? '' : value.split(';')[0];
        },
    };
    vm.runInNewContext(source, {document, location: {protocol: 'https:'}});
    assert.equal(writes.length, 0, 'No cookie probe on page load');
    assert.equal(reads, 0);
    handlers.change();
    if (choice === 'True') {
        assert.equal(status.value, blocked ? 'blocked' : 'supported');
        assert.ok(writes[0].includes('Secure'));
        assert.ok(writes.at(-1).includes('Max-Age=0'));
        assert.equal(cookie, '');
    } else {
        assert.equal(status.value, choice === null ? 'not_tested' : 'declined');
        assert.equal(writes.length, 0);
        assert.equal(reads, 0);
    }
    handlers.submit();
    return status.value;
}
run(null, false);
run('False', false);
run('True', false);
run('True', true);
console.log('Cookie probe: no choice, refusal, supported and blocked cases passed.');
