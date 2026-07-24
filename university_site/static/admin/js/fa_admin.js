/* Persian labels for Jazzmin leftovers + global admin magnifier search */
(function () {
  function faSearchPlaceholders() {
    document.querySelectorAll('input[type="search"], input.form-control-navbar').forEach(function (el) {
      if (!el.placeholder) return;
      el.placeholder = el.placeholder
        .replace(/^Search\s+/i, 'جستجو ')
        .replace(/^Search$/i, 'جستجو');
    });
  }
  function faButtons() {
    document.querySelectorAll('a.addlink, a.changelink, a.viewlink, button').forEach(function (el) {
      var t = (el.textContent || '').trim();
      if (t === 'Add') el.textContent = 'افزودن';
      else if (t === 'Change') el.textContent = 'ویرایش';
      else if (t === 'View') el.textContent = 'مشاهده';
      else if (t === 'Go') el.textContent = 'برو';
      else if (t === 'Search') el.textContent = 'جستجو';
      else if (t === 'Delete') el.textContent = 'حذف';
    });
  }

  function injectAdminNavSearch() {
    if (document.getElementById('adminNavMegaSearch')) return;
    var navbar = document.querySelector('.main-header .navbar-nav') ||
                 document.querySelector('nav.main-header .navbar-nav.ml-auto') ||
                 document.querySelector('.main-header .navbar-nav.ml-auto');
    var header = document.querySelector('.main-header .navbar') || document.querySelector('nav.main-header');
    if (!header) return;

    var wrap = document.createElement('div');
    wrap.id = 'adminNavMegaSearch';
    wrap.className = 'admin-nav-mega';
    wrap.innerHTML =
      '<div class="admin-nav-mega-box">' +
        '<span class="admin-nav-mega-icon" aria-hidden="true">' +
          '<svg viewBox="0 0 24 24" width="18" height="18" fill="none">' +
            '<circle cx="11" cy="11" r="7" stroke="currentColor" stroke-width="2.2"/>' +
            '<path d="M20 20l-3.5-3.5" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/>' +
          '</svg>' +
        '</span>' +
        '<input type="search" id="adminNavSearchInput" class="admin-nav-mega-input" ' +
               'placeholder="جستجوی بخش‌های پنل…" autocomplete="off" aria-label="جستجوی ادمین">' +
        '<div class="admin-nav-mega-results" id="adminNavSearchResults" hidden></div>' +
      '</div>';

    // Prefer placing before user menu
    if (navbar && navbar.parentNode) {
      header.insertBefore(wrap, navbar);
    } else {
      header.appendChild(wrap);
    }

    var input = document.getElementById('adminNavSearchInput');
    var results = document.getElementById('adminNavSearchResults');
    var cache = null;
    var timer = null;

    function norm(s) {
      return (s || '').toString().trim().toLowerCase()
        .replace(/ي/g, 'ی').replace(/ك/g, 'ک');
    }

    function ensureIndex(cb) {
      if (cache) return cb(cache);
      fetch('/admin/nav-search.json', { credentials: 'same-origin' })
        .then(function (r) { return r.ok ? r.json() : { items: [] }; })
        .then(function (data) {
          cache = (data && data.items) || [];
          cb(cache);
        })
        .catch(function () { cache = []; cb(cache); });
    }

    function render(q) {
      q = norm(q);
      if (!q) {
        results.hidden = true;
        results.innerHTML = '';
        return;
      }
      ensureIndex(function (items) {
        var matches = items.filter(function (item) {
          var hay = norm(item.name + ' ' + item.app + ' ' + (item.help || ''));
          return hay.indexOf(q) !== -1 && item.url;
        }).slice(0, 10);
        if (!matches.length) {
          results.hidden = false;
          results.innerHTML = '<div class="admin-nav-mega-empty">موردی پیدا نشد</div>';
          return;
        }
        results.hidden = false;
        results.innerHTML = matches.map(function (item) {
          return '<a class="admin-nav-mega-hit" href="' + item.url + '">' +
            '<strong>' + item.name + '</strong>' +
            '<small>' + item.app + '</small>' +
            '</a>';
        }).join('');
      });
    }

    input.addEventListener('input', function () {
      clearTimeout(timer);
      timer = setTimeout(function () { render(input.value); }, 120);
    });
    input.addEventListener('focus', function () {
      if (input.value) render(input.value);
    });
    document.addEventListener('click', function (e) {
      if (!e.target.closest('#adminNavMegaSearch')) {
        results.hidden = true;
      }
    });
    document.addEventListener('keydown', function (e) {
      if ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K')) {
        e.preventDefault();
        input.focus();
        input.select();
      }
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    faSearchPlaceholders();
    faButtons();
    injectAdminNavSearch();
    revealFileInputs();
  });
  window.addEventListener('load', revealFileInputs);

  function revealFileInputs() {
    document.querySelectorAll('input[type="file"]').forEach(function (el) {
      el.style.display = 'block';
      el.style.visibility = 'visible';
      el.style.opacity = '1';
      el.style.width = '100%';
      el.style.maxWidth = '520px';
      el.style.padding = '12px';
      el.style.border = '2px dashed #1a73e8';
      el.style.borderRadius = '10px';
      el.style.background = '#f0f7ff';
      el.style.cursor = 'pointer';
    });
    document.querySelectorAll('.custom-file, .custom-file-input, .field-file, .field-word_file').forEach(function (el) {
      el.style.opacity = '1';
      el.style.display = 'block';
      el.style.visibility = 'visible';
    });
  }
})();
