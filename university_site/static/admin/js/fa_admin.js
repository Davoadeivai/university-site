/* Persian labels for Jazzmin leftovers (Search placeholders, etc.) */
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
  document.addEventListener('DOMContentLoaded', function () {
    faSearchPlaceholders();
    faButtons();
  });
})();
