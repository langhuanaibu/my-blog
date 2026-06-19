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
    document.body.insertBefore(texture, document.body.firstChild);
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
    document.body.classList.add('aoiblog-post');
    addPaperTexture();
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
