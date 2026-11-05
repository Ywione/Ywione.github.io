(function () {
  var seriesRoot = document.querySelector('.qds-series');
  if (seriesRoot) {
    fetch(seriesRoot.dataset.url).then(function (response) {
      if (!response.ok) throw new Error('Download unavailable');
      return response.json();
    }).then(function (data) {
      var records = data.records.slice().sort(function (a, b) { return (b.date || '').localeCompare(a.date || '') || a.series.localeCompare(b.series); });
      var controls = {}, page = 0, pageSize = 100, filtered = [];
      function basis(r) { return r.classification || r.index_base || ''; }
      function field(r, key) { return key === 'year' ? (r.date ? r.date.slice(0, 4) : 'Year missing') : key === 'basis' ? basis(r) : r[key]; }
      ['series', 'year', 'frequency', 'measure', 'basis'].forEach(function (key) {
        var select = document.getElementById('ts-' + key);
        controls[key] = select;
        Array.from(new Set(records.map(function (r) { return field(r, key); }).filter(Boolean))).sort().forEach(function (value) {
          var option = document.createElement('option'); option.value = value; option.textContent = value; select.appendChild(option);
        });
        if (key === 'measure') select.value = 'Value';
        select.addEventListener('change', function () { page = 0; filterRecords(); });
      });
      function render() {
        var body = document.getElementById('ts-body'); body.replaceChildren();
        filtered.slice(page * pageSize, (page + 1) * pageSize).forEach(function (r) {
          var row = document.createElement('tr');
          var status = [r.status, r.revision ? 'Revision: ' + r.revision : '', r.availability].filter(Boolean).join('; ');
          [r.date || r.period, r.series, r.value === null ? r.source_marker || '—' : Number(r.value.toPrecision(12)).toLocaleString('en-US', {maximumFractionDigits:8}), r.units, r.frequency, basis(r), status].forEach(function (value, i) {
            var cell = document.createElement('td'); cell.textContent = value;
            if (i === 2) cell.className = 'qds-number';
            if (r.availability) cell.classList.add('qds-unavailable');
            cell.title = r.source_sheet + '!' + r.source_cell; row.appendChild(cell);
          }); body.appendChild(row);
        });
        document.getElementById('ts-count').textContent = filtered.length.toLocaleString() + ' observations' + (filtered.length ? ' · showing ' + (page * pageSize + 1) + '–' + Math.min((page + 1) * pageSize, filtered.length) : ' match these filters');
        document.getElementById('ts-page').textContent = 'Page ' + (page + 1) + ' of ' + Math.max(1, Math.ceil(filtered.length / pageSize));
        document.getElementById('ts-prev').disabled = page === 0;
        document.getElementById('ts-next').disabled = (page + 1) * pageSize >= filtered.length;
      }
      function filterRecords() {
        filtered = records.filter(function (r) { return Object.keys(controls).every(function (key) { return !controls[key].value || field(r, key) === controls[key].value; }); }); render();
      }
      ['prev', 'next'].forEach(function (direction) { document.getElementById('ts-' + direction).addEventListener('click', function () { page += direction === 'next' ? 1 : -1; render(); seriesRoot.querySelector('.qds-table-shell').scrollTop = 0; }); });
      seriesRoot.querySelector('.qds-series-controls').hidden = false;
      seriesRoot.querySelector('.qds-pagination').hidden = false;
      filterRecords();
    }).catch(function () { document.getElementById('ts-count').textContent = 'Interactive view could not load. The preview and complete Excel/CSV downloads remain available.'; });
  }
  var controls = document.querySelector('.qds-controls');
  if (controls) {
    var search = document.getElementById('qds-search');
    var subject = document.getElementById('qds-subject');
    var count = document.getElementById('qds-count');
    var empty = document.getElementById('qds-empty');
    var entries = Array.from(document.querySelectorAll('.qds-entry'));
    var searchable = entries.map(function (entry) { return entry.textContent.toLowerCase().replace(/\s+/g, ' '); });
    function filter() {
      var terms = search.value.toLowerCase().trim().split(/\s+/).filter(Boolean);
      var visible = 0;
      entries.forEach(function (entry, index) {
        var match = (!subject.value || entry.dataset.subject === subject.value) && terms.every(function (term) { return searchable[index].indexOf(term) !== -1; });
        entry.hidden = !match;
        if (match) visible++;
      });
      count.textContent = visible + (visible === 1 ? ' table' : ' tables') + (visible === entries.length ? '' : ' of ' + entries.length);
      empty.hidden = visible !== 0;
    }
    controls.hidden = false;
    search.addEventListener('input', filter);
    subject.addEventListener('change', filter);
  }
  var year = document.getElementById('qds-year');
  if (year) {
    year.closest('.qds-year-control').hidden = false;
    year.addEventListener('change', function () {
      if (!/^\d{4}$/.test(year.value)) return;
      var shell = document.querySelector('.qds-table-shell');
      var row = shell.querySelector('[data-year="' + year.value + '"]');
      if (!row) return;
      var heading = shell.querySelector('thead');
      var top = row.getBoundingClientRect().top - shell.getBoundingClientRect().top + shell.scrollTop - (heading ? heading.getBoundingClientRect().height : 0);
      shell.scrollTo({ top: Math.max(0, top), behavior: 'auto' });
    });
  }
})();
