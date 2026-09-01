/* Turns any <select class="searchable"> into a type-to-search dropdown.
   The original <select> stays in the DOM (hidden) so form submission,
   the `required` attribute, and any existing onchange handler all keep
   working exactly as before - this only changes how the user picks a
   value. Call initSearchableSelects() once after the page loads (it's
   already wired up at the bottom of this file). */

function initSearchableSelects() {
  document.querySelectorAll('select.searchable').forEach(function (select) {
    if (select.dataset.searchableInit) return; // don't double-init
    select.dataset.searchableInit = '1';

    // Opt-in "add new" support: set data-quick-add-url="/some/endpoint"
    // (POSTed as {name: <typed text>}, expects JSON {ok, id, name, ...})
    // on the <select> to let the user add a brand-new option without
    // leaving the form - e.g. typing an item that doesn't exist yet
    // straight from the Sale/Purchase page instead of visiting Inventory
    // first. data-quick-add-rate-field optionally names a field in the
    // JSON response to copy onto the new option's data-rate, so any
    // existing rate-autofill (onchange) logic keeps working unchanged.
    const quickAddUrl = select.dataset.quickAddUrl || null;
    const quickAddRateField = select.dataset.quickAddRateField || null;
    const quickAddLabel = select.dataset.quickAddLabel || 'item';

    let options = Array.from(select.options).filter(function (o) { return o.value !== ''; });

    const wrapper = document.createElement('div');
    wrapper.className = 'searchable-wrap';
    wrapper.style.position = 'relative';

    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'searchable-input';
    input.autocomplete = 'off';
    input.placeholder = select.options[0] ? select.options[0].text : 'Search…';
    if (select.value) {
      const sel = options.find(function (o) { return o.value === select.value; });
      if (sel) input.value = sel.text;
    }

    const list = document.createElement('div');
    list.className = 'searchable-list';
    list.style.display = 'none';

    function renderList(filterText) {
      list.innerHTML = '';
      const term = (filterText || '').toLowerCase().trim();
      const matches = options.filter(function (o) { return o.text.toLowerCase().indexOf(term) !== -1; });
      if (matches.length === 0) {
        const empty = document.createElement('div');
        empty.className = 'searchable-empty';
        empty.textContent = 'No matches';
        list.appendChild(empty);
      } else {
        matches.forEach(function (o) {
          const item = document.createElement('div');
          item.className = 'searchable-item';
          item.textContent = o.text;
          item.addEventListener('mousedown', function (e) {
            e.preventDefault();
            select.value = o.value;
            input.value = o.text;
            list.style.display = 'none';
            select.dispatchEvent(new Event('change'));
          });
          list.appendChild(item);
        });
      }

      // "+ Add ..." row: only when quick-add is enabled on this select,
      // there's actual typed text, and it doesn't already exactly match
      // an existing option (so picking an existing item never offers to
      // re-add it).
      const exactMatch = options.some(function (o) { return o.text.toLowerCase() === term; });
      if (quickAddUrl && term && !exactMatch) {
        const addRow = document.createElement('div');
        addRow.className = 'searchable-item searchable-add';
        addRow.textContent = '+ Add "' + filterText.trim() + '" as a new ' + quickAddLabel;
        addRow.addEventListener('mousedown', function (e) {
          e.preventDefault();
          quickAdd(filterText.trim(), addRow);
        });
        list.appendChild(addRow);
      }
    }

    function quickAdd(name, addRow) {
      addRow.textContent = 'Adding "' + name + '"…';
      const body = new URLSearchParams({ name: name });
      fetch(quickAddUrl, { method: 'POST', body: body, credentials: 'same-origin',
                            headers: { 'X-CSRFToken': window.CSRF_TOKEN || '' } })
        .then(function (r) { return r.json().then(function (data) { return { status: r.status, data: data }; }); })
        .then(function (res) {
          if (!res.data.ok) {
            addRow.textContent = res.data.error || 'Could not add that item.';
            addRow.classList.add('searchable-error');
            return;
          }
          const opt = document.createElement('option');
          opt.value = res.data.id;
          opt.textContent = res.data.name;
          if (quickAddRateField && res.data[quickAddRateField] !== undefined) {
            opt.dataset.rate = res.data[quickAddRateField];
          }
          if (res.data.sale_rate !== undefined) {
            opt.dataset.sale = res.data.sale_rate;
          }
          opt.dataset.stock = 0; // a freshly quick-added item always starts at 0 stock
          select.appendChild(opt);
          options = options.concat([opt]);
          select.value = res.data.id;
          input.value = res.data.name;
          list.style.display = 'none';
          select.dispatchEvent(new Event('change'));
        })
        .catch(function () {
          addRow.textContent = 'Could not reach the server - try again.';
          addRow.classList.add('searchable-error');
        });
    }

    input.addEventListener('focus', function () {
      renderList(input.value === (select.selectedOptions[0] && select.selectedOptions[0].text) ? '' : input.value);
      list.style.display = '';
    });
    input.addEventListener('input', function () {
      // Deliberately does NOT touch select.value while typing - the
      // previously confirmed selection (if any) stays intact until the
      // user actually clicks a new option. This means typing to browse
      // and then clicking away without picking anything safely keeps
      // whatever was already selected, instead of silently clearing it.
      renderList(input.value);
      list.style.display = '';
    });
    input.addEventListener('blur', function () {
      setTimeout(function () {
        list.style.display = 'none';
        // reflect whatever the select's real value currently is (set
        // only by actually clicking an option - see below)
        const sel = options.find(function (o) { return o.value === select.value; });
        input.value = sel ? sel.text : '';
      }, 150);
    });

    select.style.display = 'none';
    select.parentNode.insertBefore(wrapper, select);
    wrapper.appendChild(input);
    wrapper.appendChild(list);
    wrapper.appendChild(select);
  });
}

document.addEventListener('DOMContentLoaded', initSearchableSelects);
