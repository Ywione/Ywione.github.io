(function () {
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
