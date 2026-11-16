(() => {
 const root = document.querySelector('[data-household-questions]');
 if (!root) return;
 function update() {
   const selected = root.querySelector('[name="rent_status"]:checked');
   const show = !!selected && selected.value === 'True';
   document.getElementById('rent-amount').hidden = !show;
   root.querySelectorAll('[name="rent_category"]').forEach(field => {
     if (!show) field.checked = false;
   });
 }
 root.querySelectorAll('[name="rent_status"]').forEach(field => field.addEventListener('change', update));
 update();
})();
