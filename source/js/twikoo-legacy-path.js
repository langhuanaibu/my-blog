(function () {
  var mount = document.querySelector('[data-twikoo-path]');
  if (!mount) return;

  function loadScript(src, callback) {
    var existing = document.querySelector('script[src="' + src + '"]');
    if (existing) {
      existing.addEventListener('load', callback, { once: true });
      if (window.twikoo) callback();
      return;
    }

    var script = document.createElement('script');
    script.src = src;
    script.async = true;
    script.onload = callback;
    document.head.appendChild(script);
  }

  loadScript('https://cdn.staticfile.net/twikoo/1.6.32/twikoo.all.min.js', function () {
    if (!window.twikoo) return;
    window.twikoo.init({
      envId: 'https://twikoo.aoiblog.top',
      el: '#' + mount.id,
      path: mount.getAttribute('data-twikoo-path') || window.location.pathname,
      lang: 'zh-CN'
    });
  });
})();
