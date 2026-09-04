/* داشبورد ادمین — جستجو، علاقه‌مندی، اخیراً بازشده، صف کار.
   قبلاً درون index.html بود؛ اینجا آمد تا قابل کش و سازگار با CSP باشد. */
(function () {
    'use strict';

    var FAV_KEY = 'adminDashFavorites';
    var RECENT_KEY = 'adminDashRecent';

    var input = document.getElementById('admin-global-search');
    var resultsEl = document.getElementById('adminSearchResults');
    var filter = 'all';
    var catalog = [];

    try {
        var raw = document.getElementById('admin-catalog-data');
        catalog = raw ? JSON.parse(raw.textContent || '[]') : [];
    } catch (e) {
        catalog = [];
    }

    var byKey = {};
    catalog.forEach(function (item) { byKey[item.key] = item; });

    function norm(s) {
        return (s || '').toString().trim().toLowerCase()
            .replace(/ي/g, 'ی').replace(/ك/g, 'ک');
    }

    /* متن را به‌جای innerHTML به‌صورت گره متنی می‌سازد تا تزریق ممکن نباشد */
    function el(tag, cls, text) {
        var n = document.createElement(tag);
        if (cls) n.className = cls;
        if (text != null) n.textContent = text;
        return n;
    }

    function loadList(key) {
        try { return JSON.parse(localStorage.getItem(key) || '[]'); }
        catch (e) { return []; }
    }
    function saveList(key, arr) {
        try { localStorage.setItem(key, JSON.stringify(arr)); } catch (e) { /* quota */ }
    }

    function renderChipBar(barId, listId, keys) {
        var bar = document.getElementById(barId);
        var list = document.getElementById(listId);
        if (!bar || !list) return;
        list.textContent = '';
        var shown = 0;
        keys.forEach(function (k) {
            var item = byKey[k];
            if (!item || !item.url) return;
            var a = el('a', 'admin-fav-chip', item.name);
            a.href = item.url;
            list.appendChild(a);
            shown++;
        });
        bar.hidden = shown === 0;
    }

    function refreshStars() {
        var favs = loadList(FAV_KEY);
        document.querySelectorAll('.admin-star-btn').forEach(function (btn) {
            var on = favs.indexOf(btn.getAttribute('data-key')) !== -1;
            btn.textContent = on ? '★' : '☆';
            btn.classList.toggle('is-on', on);
        });
        renderChipBar('adminFavBar', 'adminFavList', favs);
        renderChipBar('adminRecentBar', 'adminRecentList', loadList(RECENT_KEY));
    }

    document.querySelectorAll('.admin-star-btn').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            var key = btn.getAttribute('data-key');
            var favs = loadList(FAV_KEY);
            var i = favs.indexOf(key);
            if (i === -1) favs.unshift(key); else favs.splice(i, 1);
            saveList(FAV_KEY, favs.slice(0, 12));
            refreshStars();
        });
    });

    document.querySelectorAll('.admin-track-link').forEach(function (a) {
        a.addEventListener('click', function () {
            var row = a.closest('.admin-feature-row');
            if (!row) return;
            var key = row.getAttribute('data-key');
            if (!key) return;
            var recent = loadList(RECENT_KEY).filter(function (k) { return k !== key; });
            recent.unshift(key);
            saveList(RECENT_KEY, recent.slice(0, 8));
        });
    });

    /* ── فیلتر و جستجو ─────────────────────────────────────────── */

    function applyPageFilter(q, sectionFilter) {
        document.querySelectorAll('.admin-feature-row').forEach(function (row) {
            var hay = norm(
                row.getAttribute('data-name') + ' ' +
                row.getAttribute('data-app') + ' ' +
                (row.getAttribute('data-help') || '')
            );
            var sectionOk = (sectionFilter === 'all') ||
                norm(row.getAttribute('data-section')) === norm(sectionFilter);
            var qOk = !q || hay.indexOf(q) !== -1;
            row.style.display = (sectionOk && qOk) ? '' : 'none';
        });
        // بلوک گروهی که همه ردیف‌هایش پنهان شده‌اند را جمع کن.
        //
        // گروه‌ها حالا details هستند و جمع‌شده باز می‌شوند؛ پس هنگام
        // جستجو باید خودشان باز شوند، وگرنه کاربر نتیجه‌ای می‌بیند که
        // پشتِ یک عنوانِ بسته پنهان است. با پاک‌شدنِ جستجو، به همان
        // حالت اولیه برمی‌گردند: فقط گروه نخست باز.
        var searching = !!q || sectionFilter !== 'all';
        document.querySelectorAll('.admin-section-block').forEach(
            function (block, index) {
                var visible = block.querySelectorAll(
                    '.admin-feature-row:not([style*="display: none"])'
                ).length;
                block.hidden = visible === 0;
                if (block.tagName === 'DETAILS') {
                    block.open = searching ? visible > 0 : index === 0;
                }
            });
    }

    function renderResults(value) {
        if (!resultsEl) return;
        var q = norm(value);
        if (!q) {
            resultsEl.hidden = true;
            resultsEl.textContent = '';
            applyPageFilter('', filter);
            return;
        }

        var matches = catalog.filter(function (item) {
            var hay = norm(item.name + ' ' + item.app_name + ' ' + (item.help || ''));
            var sectionOk = filter === 'all' || norm(item.section) === norm(filter);
            return sectionOk && hay.indexOf(q) !== -1 && item.url;
        }).slice(0, 12);

        applyPageFilter(q, filter);

        resultsEl.textContent = '';
        resultsEl.hidden = false;
        if (!matches.length) {
            resultsEl.appendChild(el('div', 'admin-mega-empty', 'موردی پیدا نشد'));
            return;
        }
        matches.forEach(function (item) {
            var a = el('a', 'admin-mega-hit');
            a.href = item.url;
            a.appendChild(el('span', 'admin-mega-hit-title', item.name));
            a.appendChild(el('span', 'admin-mega-hit-meta',
                item.app_name + ' — ' + (item.help || '')));
            resultsEl.appendChild(a);
        });
    }

    if (input) {
        input.addEventListener('input', function () { renderResults(input.value); });
        input.addEventListener('focus', function () {
            if (input.value) renderResults(input.value);
        });
        document.addEventListener('keydown', function (e) {
            if ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K')) {
                e.preventDefault();
                input.focus();
                input.select();
            }
            if (e.key === 'Escape' && resultsEl) {
                resultsEl.hidden = true;
                input.blur();
            }
        });
    }

    document.querySelectorAll('#adminSearchFilters .admin-filter-chip').forEach(function (btn) {
        btn.addEventListener('click', function () {
            document.querySelectorAll('#adminSearchFilters .admin-filter-chip')
                .forEach(function (b) { b.classList.remove('active'); });
            btn.classList.add('active');
            filter = btn.getAttribute('data-filter') || 'all';
            renderResults(input ? input.value : '');
        });
    });

    /* ── تعویض نمای گروهی / الفبایی ────────────────────────────── */

    document.querySelectorAll('.admin-view-btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var view = btn.getAttribute('data-view');
            document.querySelectorAll('.admin-view-btn')
                .forEach(function (b) { b.classList.remove('active'); });
            btn.classList.add('active');
            var s = document.getElementById('viewSections');
            var c = document.getElementById('viewColumns');
            if (s) s.hidden = view !== 'sections';
            if (c) c.hidden = view !== 'columns';
        });
    });

    /* ── شمارنده‌های زنده ───────────────────────────────────────
       نسخه قبلی هر ۶۰ ثانیه برای همیشه پول می‌زد، حتی روی تب پنهان.
       حالا فقط وقتی تب دیده می‌شود و با فاصله بیشتر. */

    var POLL_MS = 120000;
    var pollTimer = null;

    function refreshCounters() {
        if (document.visibilityState !== 'visible') return;
        fetch('/admin/live-counters.json', { credentials: 'same-origin' })
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (data) {
                if (!data || !data.queue) return;
                data.queue.forEach(function (item) {
                    var node = document.querySelector('[data-count-for="' + item.key + '"]');
                    if (!node) return;
                    node.textContent = item.count;
                    var card = node.closest('.admin-queue-card');
                    if (!card) return;
                    card.classList.toggle('is-clear', !item.count);
                    card.classList.toggle('is-urgent', !!item.count && item.urgent);
                    card.classList.toggle('is-open', !!item.count && !item.urgent);
                });
                var total = document.querySelector('.admin-worklist-total');
                if (total && typeof data.total_pending === 'number') {
                    total.textContent = data.total_pending
                        ? data.total_pending + ' مورد نیازمند رسیدگی'
                        : 'همه‌چیز رسیدگی شده ✓';
                    total.classList.toggle('has', !!data.total_pending);
                }
            })
            .catch(function () { /* شبکه قطع — بی‌صدا رد شو */ });
    }

    function startPolling() {
        stopPolling();
        pollTimer = setInterval(refreshCounters, POLL_MS);
    }
    function stopPolling() {
        if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
    }

    document.addEventListener('visibilitychange', function () {
        if (document.visibilityState === 'visible') {
            refreshCounters();
            startPolling();
        } else {
            stopPolling();
        }
    });

    refreshStars();
    startPolling();
})();
