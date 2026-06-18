(function () {
  var path = window.location.pathname.replace(/\/+$/, '') || '/';
  var isHome = path === '/' || /^\/page\/\d+$/.test(path);

  if (!isHome) return;

  document.body.classList.add('aoiblog-home');

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
