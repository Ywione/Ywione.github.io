(function () {
  var root = document.documentElement;
  var stored;
  try { stored = localStorage.getItem('ywione-theme'); } catch (_) {}
  if (stored === 'light' || stored === 'dark') root.dataset.theme = stored;
  document.addEventListener('DOMContentLoaded', function () {
    var button = document.getElementById('theme-toggle');
    if (!button) return;
    var preference = window.matchMedia('(prefers-color-scheme: dark)');
    function dark() { return root.dataset.theme ? root.dataset.theme === 'dark' : preference.matches; }
    function update() {
      var next = dark() ? 'light' : 'dark';
      button.setAttribute('aria-label', 'Switch to ' + next + ' theme');
      button.querySelector('.theme-label').textContent = next === 'dark' ? 'Dark' : 'Light';
    }
    button.hidden = false;
    button.addEventListener('click', function () {
      root.dataset.theme = dark() ? 'light' : 'dark';
      try { localStorage.setItem('ywione-theme', root.dataset.theme); } catch (_) {}
      update();
    });
    if (preference.addEventListener) preference.addEventListener('change', update);
    update();
  });
})();
