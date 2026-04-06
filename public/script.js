document.addEventListener('DOMContentLoaded', function () {
  const typewriterElement = document.getElementById('typewriter-text');
  if (typewriterElement) {
    const text = '乌幕屏，海相续，举眼茫茫，静听细浪语';
    let index = 0;
    const cursor = document.createElement('span');
    cursor.className = 'typewriter-cursor';
    cursor.innerHTML = '&nbsp;';

    function typeWriter() {
      if (index < text.length) {
        typewriterElement.textContent = text.substring(0, index + 1);
        typewriterElement.appendChild(cursor);
        index++;
        setTimeout(typeWriter, 100);
      }
    }

    setTimeout(typeWriter, 500);
  }

  const themeToggle = document.getElementById('theme-toggle');
  const root = document.documentElement;

  function isDarkTheme() {
    return root.getAttribute('data-theme') === 'dark';
  }

  function updateThemeLabel() {
    if (themeToggle) {
      themeToggle.textContent = isDarkTheme() ? '🌙' : '🌞';
    }
    const themeBtn = document.getElementById('float-theme-btn');
    if (themeBtn) {
      themeBtn.textContent = isDarkTheme() ? '🌙' : '🌞';
    }
  }

  if (themeToggle) {
    updateThemeLabel();
    themeToggle.addEventListener('click', () => {
      if (isDarkTheme()) {
        root.removeAttribute('data-theme');
        localStorage.setItem('theme', 'light');
      } else {
        root.setAttribute('data-theme', 'dark');
        localStorage.setItem('theme', 'dark');
      }
      updateThemeLabel();
    });
  }

  document.querySelectorAll('.site-nav a[href^="#"], .site-nav a[href^="/#"]').forEach((link) => {
    link.addEventListener('click', function (e) {
      const href = this.getAttribute('href');
      const hash = href.includes('#') ? href.slice(href.indexOf('#')) : '';
      if (!hash) return;

      const isCurrentPageAnchor = href.startsWith('#');
      const isHomeAnchorOnHomePage = href.startsWith('/#') && window.location.pathname === '/';
      if (!isCurrentPageAnchor && !isHomeAnchorOnHomePage) return;

      const targetElement = document.querySelector(hash);
      if (!targetElement) return;

      e.preventDefault();
      const headerHeight = document.querySelector('.site-header')?.offsetHeight || 88;
      const targetPosition = targetElement.getBoundingClientRect().top + window.scrollY - headerHeight - 12;
      window.scrollTo({ top: targetPosition, behavior: 'smooth' });
    });
  });

  const floatingMenu = document.querySelector('.floating-menu');
  const mainBtn = document.getElementById('floating-main-btn');
  const topBtn = document.getElementById('float-top-btn');
  const randomBtn = document.getElementById('float-random-btn');
  const themeBtn = document.getElementById('float-theme-btn');

  if (floatingMenu && mainBtn) {
    mainBtn.addEventListener('click', () => {
      floatingMenu.classList.toggle('active');
    });

    document.addEventListener('click', (e) => {
      if (!floatingMenu.contains(e.target)) {
        floatingMenu.classList.remove('active');
      }
    });

    if (topBtn) {
      topBtn.addEventListener('click', () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
        floatingMenu.classList.remove('active');
      });

      window.addEventListener('scroll', () => {
        topBtn.style.display = window.scrollY > 300 ? 'flex' : 'none';
      });

      if (window.scrollY <= 300) {
        topBtn.style.display = 'none';
      }
    }

    if (randomBtn) {
      randomBtn.addEventListener('click', () => {
        if (typeof blogArticles !== 'undefined' && blogArticles.length > 0) {
          const randomIndex = Math.floor(Math.random() * blogArticles.length);
          const randomId = blogArticles[randomIndex].id;
          if (window.location.pathname.includes('articles.html')) {
            if (typeof showArticle === 'function') {
              showArticle(randomId);
            }
            history.pushState(null, '', '#' + randomId);
          } else {
            window.location.href = '/articles.html#' + randomId;
          }
        } else {
          window.location.href = '/articles.html';
        }
        floatingMenu.classList.remove('active');
      });
    }

    if (themeBtn && themeToggle) {
      updateThemeLabel();
      themeBtn.addEventListener('click', () => {
        themeToggle.click();
        floatingMenu.classList.remove('active');
      });
    }
  }
});
