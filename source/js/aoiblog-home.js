(function () {
  var path = window.location.pathname.replace(/\/+$/, '') || '/';
  var isHome = path === '/' || /^\/page\/\d+$/.test(path);
  var isPost = /^\/\d{4}\/\d{2}\/\d{2}\//.test(path + '/');

  function isDarkTheme() {
    return document.documentElement.getAttribute('data-user-color-scheme') === 'dark';
  }

  function pickColor(colors) {
    return colors[Math.floor(Math.random() * colors.length)];
  }

  function addPaperTexture() {
    if (document.querySelector('.aoiblog-paper-texture')) return;

    var texture = document.createElement('div');
    texture.className = 'aoiblog-paper-texture';
    texture.setAttribute('aria-hidden', 'true');
    document.body.insertBefore(texture, document.body.firstChild);
  }

  function initReadingProgress(content) {
    if (document.querySelector('.aoi-reading-progress')) return;

    var progress = document.createElement('div');
    progress.className = 'aoi-reading-progress';
    progress.setAttribute('role', 'progressbar');
    progress.setAttribute('aria-label', '文章阅读进度');
    progress.setAttribute('aria-valuemin', '0');
    progress.setAttribute('aria-valuemax', '100');
    progress.setAttribute('aria-valuenow', '0');
    progress.innerHTML = '<span class="aoi-reading-progress__bar"></span>';
    document.body.appendChild(progress);

    var bar = progress.querySelector('.aoi-reading-progress__bar');
    var articleTop = 0;
    var articleHeight = 0;
    var ticking = false;
    var desktopQuery = window.matchMedia('(min-width: 992px)');

    function update() {
      ticking = false;
      var scrollRange = articleHeight - window.innerHeight;
      var isShortArticle = scrollRange <= Math.max(120, window.innerHeight * 0.1);
      var ratio = scrollRange > 0 ? (window.scrollY - articleTop) / scrollRange : 0;
      ratio = Math.max(0, Math.min(1, ratio));

      progress.hidden = isShortArticle;
      bar.style.transform = 'scaleX(' + ratio + ')';
      progress.setAttribute('aria-valuenow', String(Math.round(ratio * 100)));

      document.body.classList.toggle(
        'aoi-reading-active',
        desktopQuery.matches && window.scrollY > articleTop + 80
      );
    }

    function requestUpdate() {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(update);
    }

    function measure() {
      var rect = content.getBoundingClientRect();
      articleTop = window.scrollY + rect.top;
      articleHeight = rect.height;
      requestUpdate();
    }

    window.addEventListener('scroll', requestUpdate, { passive: true });
    window.addEventListener('resize', measure, { passive: true });
    if (desktopQuery.addEventListener) {
      desktopQuery.addEventListener('change', requestUpdate);
    }
    if (typeof ResizeObserver === 'function') {
      new ResizeObserver(measure).observe(content);
    }
    measure();
  }

  function initCodeWrapping(markdown) {
    var candidates = markdown.querySelectorAll('figure.highlight, pre');

    candidates.forEach(function (block) {
      if (block.tagName === 'PRE' && block.closest('figure.highlight')) return;
      if (block.classList.contains('aoi-code-block')) return;

      block.classList.add('aoi-code-block');

      var button = document.createElement('button');
      button.type = 'button';
      button.className = 'aoi-code-wrap-toggle';
      button.setAttribute('aria-label', '切换代码折行');
      button.setAttribute('aria-pressed', 'false');
      button.setAttribute('title', '切换代码折行');
      button.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h12a4 4 0 0 1 0 8H9"/><path d="m12 12-3 3 3 3"/><path d="M4 17h2"/></svg>';

      button.addEventListener('click', function () {
        var wrapped = block.classList.toggle('is-code-wrapped');
        button.setAttribute('aria-pressed', String(wrapped));
      });

      block.appendChild(button);
    });
  }

  function initScrollableTables(markdown) {
    markdown.querySelectorAll('table').forEach(function (table) {
      if (table.closest('figure.highlight') || table.closest('.aoi-table-scroll')) return;

      var wrapper = document.createElement('div');
      wrapper.className = 'aoi-table-scroll';
      wrapper.tabIndex = 0;
      wrapper.setAttribute('role', 'region');
      wrapper.setAttribute('aria-label', '可横向滚动的表格');
      table.classList.add('aoi-content-table');
      table.parentNode.insertBefore(wrapper, table);
      wrapper.appendChild(table);

      function updateScrollState() {
        var canScroll = wrapper.scrollWidth > wrapper.clientWidth + 1;
        var atStart = wrapper.scrollLeft <= 1;
        var atEnd = wrapper.scrollLeft + wrapper.clientWidth >= wrapper.scrollWidth - 1;
        wrapper.classList.toggle('is-scrollable', canScroll);
        wrapper.classList.toggle('is-at-start', atStart);
        wrapper.classList.toggle('is-at-end', atEnd);
      }

      wrapper.addEventListener('scroll', updateScrollState, { passive: true });
      window.addEventListener('resize', updateScrollState, { passive: true });
      window.requestAnimationFrame(updateScrollState);
    });
  }

  function buildMobileToc(tocBody) {
    if (document.getElementById('aoi-toc-panel')) return;

    var overlay = document.createElement('div');
    overlay.className = 'aoi-toc-overlay';
    overlay.id = 'aoi-toc-overlay';
    overlay.setAttribute('aria-hidden', 'true');
    document.body.appendChild(overlay);

    var panel = document.createElement('div');
    panel.className = 'aoi-toc-panel';
    panel.id = 'aoi-toc-panel';
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-modal', 'true');
    panel.setAttribute('aria-hidden', 'true');
    panel.setAttribute('aria-labelledby', 'aoi-toc-panel-title');
    panel.setAttribute('inert', '');
    panel.innerHTML = '<div class="aoi-toc-panel__header"><span class="aoi-toc-panel__title" id="aoi-toc-panel-title">文章目录</span><button type="button" class="aoi-toc-panel__close" id="aoi-toc-close" aria-label="关闭目录">\u2715</button></div><div class="aoi-toc-panel__body" id="aoi-toc-panel-body"></div>';
    document.body.appendChild(panel);

    var panelBody = document.getElementById('aoi-toc-panel-body');
    var clonedToc = tocBody.cloneNode(true);
    clonedToc.id = 'aoi-mobile-toc-list';
    panelBody.appendChild(clonedToc);

    var button = document.createElement('button');
    button.type = 'button';
    button.className = 'aoi-mobile-toc-btn';
    button.id = 'aoi-toc-btn';
    button.setAttribute('aria-label', '文章目录');
    button.setAttribute('aria-controls', 'aoi-toc-panel');
    button.setAttribute('aria-expanded', 'false');
    button.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16"/></svg>';
    document.body.appendChild(button);

    var closeButton = document.getElementById('aoi-toc-close');
    var returnFocus = null;

    function syncActiveHeading() {
      var activeHrefs = Array.prototype.map.call(
        tocBody.querySelectorAll('.tocbot-active-link'),
        function (link) { return link.getAttribute('href'); }
      );

      panelBody.querySelectorAll('.tocbot-link').forEach(function (link) {
        link.classList.toggle(
          'tocbot-active-link',
          activeHrefs.indexOf(link.getAttribute('href')) !== -1
        );
      });
    }

    function openPanel() {
      returnFocus = document.activeElement;
      panel.classList.add('active');
      overlay.classList.add('active');
      document.body.classList.add('aoi-toc-open');
      panel.setAttribute('aria-hidden', 'false');
      panel.removeAttribute('inert');
      overlay.setAttribute('aria-hidden', 'false');
      button.setAttribute('aria-expanded', 'true');
      closeButton.focus();
    }

    function closePanel() {
      if (!panel.classList.contains('active')) return;
      panel.classList.remove('active');
      overlay.classList.remove('active');
      document.body.classList.remove('aoi-toc-open');
      panel.setAttribute('aria-hidden', 'true');
      panel.setAttribute('inert', '');
      overlay.setAttribute('aria-hidden', 'true');
      button.setAttribute('aria-expanded', 'false');
      if (returnFocus && typeof returnFocus.focus === 'function') {
        returnFocus.focus();
      }
    }

    button.addEventListener('click', function () {
      if (panel.classList.contains('active')) {
        closePanel();
      } else {
        openPanel();
      }
    });
    overlay.addEventListener('click', closePanel);
    closeButton.addEventListener('click', closePanel);
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') {
        closePanel();
        return;
      }
      if (event.key !== 'Tab' || !panel.classList.contains('active')) return;

      var focusable = panel.querySelectorAll(
        'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'
      );
      if (!focusable.length) return;

      var first = focusable[0];
      var last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    });
    panelBody.addEventListener('click', function (event) {
      if (event.target.closest('.tocbot-link')) closePanel();
    });

    var activeObserver = new MutationObserver(syncActiveHeading);
    activeObserver.observe(tocBody, {
      attributes: true,
      subtree: true,
      attributeFilter: ['class']
    });
    syncActiveHeading();
  }

  function initMobileToc() {
    var tocBody = document.getElementById('toc-body');
    if (!tocBody) return;

    function buildWhenReady() {
      if (tocBody.querySelector('.tocbot-link')) {
        buildMobileToc(tocBody);
        return true;
      }
      return false;
    }

    if (buildWhenReady()) return;

    var tocObserver = new MutationObserver(function () {
      if (buildWhenReady()) tocObserver.disconnect();
    });
    tocObserver.observe(tocBody, { childList: true, subtree: true });
  }

  function initPostReading() {
    if (document.body.getAttribute('data-aoi-post-reading') === 'ready') return;
    var post = document.querySelector('.post-content');
    var markdown = post && post.querySelector('.markdown-body');
    if (!post || !markdown) return;

    document.body.setAttribute('data-aoi-post-reading', 'ready');
    document.body.classList.add('aoiblog-post');
    addPaperTexture();

    initReadingProgress(markdown);
    initMobileToc();
    initCodeWrapping(markdown);
    initScrollableTables(markdown);
  }

  function addSnowCanvas() {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    if (document.querySelector('.aoiblog-snow-canvas')) return;

    var canvas = document.createElement('canvas');
    canvas.className = 'aoiblog-snow-canvas';
    document.body.insertBefore(canvas, document.body.firstChild);

    var ctx = canvas.getContext('2d');
    if (!ctx) return;

    var flakes = [];
    var frameCount = 0;
    var currentDark = isDarkTheme();

    function resize() {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    }

    function makeFlakes() {
      flakes = [];
      currentDark = isDarkTheme();

      var colors = currentDark
        ? [[255, 226, 190], [242, 199, 159], [224, 173, 120]]
        : [[255, 248, 235], [236, 198, 154], [208, 145, 88]];

      function pushLayer(count, radiusBase, radiusRange, opacityBase, opacityRange, speedBase, speedRange, swayBase, swayRange) {
        for (var i = 0; i < count; i++) {
          var color = pickColor(colors);
          var baseVy = Math.random() * speedRange + speedBase;

          flakes.push({
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height,
            r: Math.random() * radiusRange + radiusBase,
            vy: baseVy,
            baseVy: baseVy,
            opacity: Math.random() * opacityRange + opacityBase,
            color: 'rgba(' + color[0] + ',' + color[1] + ',' + color[2] + ',PLACEHOLDER)',
            swayAmp: Math.random() * swayRange + swayBase,
            swayFreq: Math.random() * 0.04 + 0.006,
            swayPhase: Math.random() * Math.PI * 2
          });
        }
      }

      pushLayer(90, 1, 1.4, 0.1, 0.08, 0.04, 0.06, 0.1, 0.3);
      pushLayer(120, 2.4, 2.4, 0.18, 0.12, 0.08, 0.12, 0.3, 0.6);
      pushLayer(42, 4.8, 3.4, 0.28, 0.16, 0.16, 0.2, 0.5, 1);
    }

    function draw() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      frameCount++;

      if (currentDark !== isDarkTheme()) makeFlakes();

      flakes.forEach(function (flake) {
        flake.vy = flake.baseVy + (Math.random() - 0.5) * flake.baseVy * 0.4;
        flake.y += flake.vy;
        flake.x += Math.sin(frameCount * flake.swayFreq + flake.swayPhase) * flake.swayAmp * 0.3;

        if (flake.y > canvas.height + 50) {
          flake.y = -50;
          flake.x = Math.random() * canvas.width;
        }

        if (flake.x > canvas.width + 50) flake.x = -50;
        if (flake.x < -50) flake.x = canvas.width + 50;

        ctx.beginPath();
        ctx.arc(flake.x, flake.y, flake.r, 0, Math.PI * 2);
        ctx.fillStyle = flake.color.replace('PLACEHOLDER', String(flake.opacity));
        ctx.fill();
      });

      requestAnimationFrame(draw);
    }

    resize();
    makeFlakes();
    draw();
    window.addEventListener('resize', function () {
      resize();
      makeFlakes();
    });
  }

  if (isPost) {
    initPostReading();
  }

  if (!isHome) return;

  document.body.classList.add('aoiblog-home');
  addSnowCanvas();

  if (path !== '/') return;

  var bannerText = document.querySelector('#banner .banner-text');
  if (!bannerText || bannerText.querySelector('.home-avatar')) return;

  var avatar = document.createElement('img');
  avatar.className = 'home-avatar';
  avatar.src = '/images/my-avatar.jpg';
  avatar.alt = 'Aoitsuki';
  avatar.loading = 'eager';

  bannerText.insertBefore(avatar, bannerText.firstChild);

})();
