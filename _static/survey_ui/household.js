(() => {
 const root = document.querySelector('[data-household-questions]'); if (!root) return;
 const update = () => {
   const s = root.querySelector('[name="rent_status_final"]:checked');
   const section = document.getElementById('rent-amount');
   const show = !!s && s.value === 'yes';
   section.hidden = !show;
   section.querySelectorAll('input').forEach(input => {
     input.disabled = !show;
     if (!show) { if (input.type === 'radio') input.checked = false; else input.value = ''; }
   });
 };
 root.querySelectorAll('[name="rent_status_final"]').forEach(x => x.addEventListener('change', update)); update();
 const search = root.querySelector('#country-search');
 const country = root.querySelector('select[name="residence_code"]');
 if (search) search.addEventListener('keydown', e => { if (e.key === 'Enter') e.preventDefault(); });
 if (search && country) search.addEventListener('input', () => {
   const query = search.value.trim().toLocaleLowerCase();
   Array.from(country.options).forEach(option => {
     option.hidden = !!query && !!option.value && option.value !== country.value && option.value !== 'prefer_not' && !option.text.toLocaleLowerCase().includes(query);
   });
 });
 const feedback = root.querySelector('[name="additional_feedback"]'); if (feedback) feedback.maxLength = 1500;
})();
