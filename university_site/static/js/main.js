// ============================================================
//  موسسه آموزش عالی علامه امینی بهنمیر - اسکریپت اصلی
// ============================================================

function escapeHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

document.addEventListener('DOMContentLoaded', function () {

    // ---- AOS Init ----
    if (typeof AOS !== 'undefined') {
        AOS.init({ duration: 700, once: true, easing: 'ease-out-cubic', offset: 60 });
    }

    // ---- Navbar Scroll Effect ----
    const navbar = document.getElementById('mainNav');
    const siteHeader = document.getElementById('siteHeader');
    if (navbar || siteHeader) {
        window.addEventListener('scroll', function () {
            const scrolled = window.scrollY > 60;
            if (navbar) navbar.classList.toggle('scrolled', scrolled);
            if (siteHeader) siteHeader.classList.toggle('compact', scrolled);
        });
    }

    // ---- Navbar: هاور دسکتاپ برای زیرمنوها (موبایل همچنان با کلیک) ----
    (function setupNavbarHoverDropdowns() {
        const mq = window.matchMedia('(min-width: 1200px) and (hover: hover)');
        const items = document.querySelectorAll('#mainNav .nav-item.dropdown');

        function onEnter(e) {
            const item = e.currentTarget;
            item.classList.add('show');
            const toggle = item.querySelector('.dropdown-toggle');
            if (toggle) toggle.setAttribute('aria-expanded', 'true');
            const menu = item.querySelector('.dropdown-menu');
            if (menu) menu.classList.add('show');
        }

        function onLeave(e) {
            const item = e.currentTarget;
            item.classList.remove('show');
            const toggle = item.querySelector('.dropdown-toggle');
            if (toggle) toggle.setAttribute('aria-expanded', 'false');
            const menu = item.querySelector('.dropdown-menu');
            if (menu) menu.classList.remove('show');
        }

        function applyMode() {
            items.forEach(function (item) {
                const toggle = item.querySelector(':scope > .dropdown-toggle');
                if (!toggle) return;

                item.removeEventListener('mouseenter', onEnter);
                item.removeEventListener('mouseleave', onLeave);

                if (mq.matches) {
                    if (toggle.hasAttribute('data-bs-toggle')) {
                        toggle.setAttribute('data-hover-toggle', toggle.getAttribute('data-bs-toggle'));
                        toggle.removeAttribute('data-bs-toggle');
                    }
                    toggle.setAttribute('aria-expanded', 'false');
                    item.addEventListener('mouseenter', onEnter);
                    item.addEventListener('mouseleave', onLeave);
                } else {
                    const saved = toggle.getAttribute('data-hover-toggle') || 'dropdown';
                    if (!toggle.hasAttribute('data-bs-toggle')) {
                        toggle.setAttribute('data-bs-toggle', saved);
                    }
                    item.classList.remove('show');
                    const menu = item.querySelector('.dropdown-menu');
                    if (menu) menu.classList.remove('show');
                }
            });
        }

        applyMode();
        if (mq.addEventListener) mq.addEventListener('change', applyMode);
        else if (mq.addListener) mq.addListener(applyMode);
    })();

    // ---- Scroll to Top Button ----
    const scrollBtn = document.getElementById('scrollTop');
    if (scrollBtn) {
        window.addEventListener('scroll', function () {
            if (window.scrollY > 300) {
                scrollBtn.classList.add('visible');
            } else {
                scrollBtn.classList.remove('visible');
            }
        });
    }

    // ---- Hero Swiper (only when present) ----
    if (typeof Swiper !== 'undefined' && document.querySelector('.hero-swiper')) {
        new Swiper('.hero-swiper', {
            loop: true,
            autoplay: { delay: 5000, disableOnInteraction: false },
            effect: 'fade',
            fadeEffect: { crossFade: true },
            pagination: { el: '.swiper-pagination', clickable: true },
            navigation: {
                nextEl: '.swiper-button-next',
                prevEl: '.swiper-button-prev',
            },
        });
    }

    // ---- Counter Animation ----
    const counters = document.querySelectorAll('.stat-number[data-target]');
    const observerOptions = { threshold: 0.15, rootMargin: '0px 0px -10% 0px' };

    function setPersianCount(el, value) {
        el.textContent = Math.floor(value).toLocaleString('fa-IR');
    }

    function animateCounter(el) {
        if (el.dataset.animated === '1') return;
        el.dataset.animated = '1';
        const target = parseInt(el.getAttribute('data-target'), 10) || 0;
        const duration = 1600;
        const start = performance.now();
        function frame(now) {
            const progress = Math.min((now - start) / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            setPersianCount(el, target * eased);
            if (progress < 1) {
                requestAnimationFrame(frame);
            } else {
                setPersianCount(el, target);
            }
        }
        requestAnimationFrame(frame);
    }

    if (counters.length) {
        if ('IntersectionObserver' in window) {
            const counterObserver = new IntersectionObserver(function (entries) {
                entries.forEach(function (entry) {
                    if (entry.isIntersecting) {
                        animateCounter(entry.target);
                        counterObserver.unobserve(entry.target);
                    }
                });
            }, observerOptions);
            counters.forEach(function (counter) { counterObserver.observe(counter); });
        }
        // Fallback: if still zero after load (observer miss / off-screen quirks)
        window.setTimeout(function () {
            counters.forEach(function (el) {
                const raw = (el.textContent || '').replace(/[^\d۰-۹0-9]/g, '');
                if (!raw || raw === '0' || raw === '۰') {
                    animateCounter(el);
                }
            });
        }, 1200);
    }

    // ---- Gallery Lightbox (safe DOM, no innerHTML for user-controlled URLs beyond img src attr) ----
    const galleryItems = document.querySelectorAll('.gallery-item');
    galleryItems.forEach(function (item) {
        item.addEventListener('click', function () {
            const imgEl = item.querySelector('img');
            const imgSrc = imgEl ? imgEl.src : '';
            if (!imgSrc) return;
            const modal = document.createElement('div');
            modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.92);z-index:9999;display:flex;align-items:center;justify-content:center;cursor:zoom-out;';
            modal.setAttribute('role', 'dialog');
            modal.setAttribute('aria-label', 'بزرگ‌نمایی تصویر');
            const big = document.createElement('img');
            big.src = imgSrc;
            big.alt = imgEl.alt || '';
            big.style.cssText = 'max-width:90vw;max-height:90vh;border-radius:12px;box-shadow:0 20px 60px rgba(0,0,0,0.5);';
            modal.appendChild(big);
            modal.addEventListener('click', function () { document.body.removeChild(modal); });
            document.body.appendChild(modal);
        });
    });

    // ---- Active Nav Link ----
    const currentPath = window.location.pathname;
    document.querySelectorAll('.nav-link-flat').forEach(function (link) {
        const href = link.getAttribute('href');
        if (href && href !== '#' && currentPath.startsWith(href) && href !== '/') {
            link.classList.add('active');
        }
    });

    // ---- Ticker (RTL: move positive X) ----
    const tickers = document.querySelectorAll('.urgent-ticker');
    tickers.forEach(function (ticker) {
        const content = ticker.innerHTML;
        ticker.innerHTML = content + ' &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ' + content;
        let pos = 0;
        setInterval(function () {
            pos += 1;
            if (pos > ticker.scrollWidth / 2) pos = 0;
            ticker.style.transform = 'translateX(' + pos + 'px)';
        }, 20);
    });

});

// ---- Chatbot Toggle ----
function toggleChatbot() {
    const widget = document.getElementById('chatbotWidget');
    const btn = document.getElementById('chatbotBtn');
    if (!widget) return;
    const open = widget.style.display === 'none' || !widget.style.display;
    widget.style.display = open ? 'block' : 'none';
    if (btn) btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (open) {
        const input = document.getElementById('chatInput');
        if (input) input.focus();
    }
}

// ---- Chatbot Responses (bot HTML is trusted static templates) ----
const chatResponses = {
    'پذیرش': 'برای پذیرش دانشجو می‌توانید از بخش پذیرش در منوی اصلی اقدام کنید.',
    'رشته': 'رشته‌های متعددی در مقاطع کاردانی، کارشناسی و ارشد داریم.',
    'شهریه': 'اطلاعات شهریه در بخش پذیرش و محاسبه‌گر شهریه موجود است.',
    'اساتید': 'لیست اعضای هیئت علمی از منوی اساتید در دسترس است.',
    'تماس': 'می‌توانید از طریق فرم تماس با ما در ارتباط باشید.',
    'کتابخانه': 'به بخش کتابخانه از منوی اصلی دسترسی دارید.',
    'default': 'سوال شما دریافت شد. کارشناسان ما در اسرع وقت پاسخ خواهند داد. می‌توانید از منوی اصلی به بخش مورد نظر دسترسی داشته باشید.'
};

function sendMsg() {
    const input = document.getElementById('chatInput');
    if (!input || !input.value.trim()) return;
    const msg = input.value.trim();
    appendMsg(msg, 'user');
    input.value = '';

    setTimeout(function () {
        let resp = chatResponses['default'];
        for (const key in chatResponses) {
            if (key !== 'default' && msg.includes(key)) { resp = chatResponses[key]; break; }
        }
        appendMsg(resp, 'bot');
    }, 700);
}

function sendQuickMsg(msg) {
    const input = document.getElementById('chatInput');
    if (!input) return;
    input.value = msg;
    sendMsg();
}

function appendMsg(text, type) {
    const container = document.getElementById('chatMessages');
    if (!container) return;
    const div = document.createElement('div');
    div.className = 'chat-msg' + (type === 'user' ? ' user-msg' : '');
    const icon = document.createElement('i');
    icon.className = type === 'bot' ? 'fas fa-robot' : 'fas fa-user';
    icon.setAttribute('aria-hidden', 'true');
    const bubble = document.createElement('div');
    bubble.className = 'msg-bubble';
    bubble.textContent = text;
    div.appendChild(icon);
    div.appendChild(bubble);
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

/* ---- Live site search (topbar) ---- */
(function () {
    var TYPE_LABEL = {
        page: 'صفحه',
        news: 'خبر',
        professor: 'استاد',
        faculty: 'استاد',
        major: 'رشته',
        academics: 'رشته',
        faq: 'FAQ',
        event: 'رویداد'
    };

    function badgeClass(type, filter) {
        var key = (type || filter || 'page').toLowerCase();
        return 'is-' + key;
    }

    function initSiteLiveSearch() {
        var root = document.getElementById('siteTopSearch');
        var input = document.getElementById('siteLiveSearch');
        var results = document.getElementById('siteSearchResults');
        var clearBtn = document.getElementById('siteSearchClear');
        if (!root || !input || !results) return;

        var timer = null;
        var lastQ = '';
        var activeIndex = -1;

        function syncClear() {
            if (!clearBtn) return;
            clearBtn.hidden = !input.value.trim();
        }

        function hideResults() {
            results.hidden = true;
            results.innerHTML = '';
            activeIndex = -1;
            root.classList.remove('is-open');
        }

        function showEmpty() {
            results.hidden = false;
            root.classList.add('is-open');
            results.innerHTML =
                '<div class="site-search-empty">' +
                '<div class="site-search-empty-title">نتیجه‌ای یافت نشد</div>' +
                '<div class="site-search-empty-text">یکی از پیشنهادها را امتحان کنید</div>' +
                '<div class="site-search-suggest">' +
                '<button type="button" data-q="پذیرش">پذیرش</button>' +
                '<button type="button" data-q="اخبار">اخبار</button>' +
                '<button type="button" data-q="رشته">رشته‌ها</button>' +
                '<button type="button" data-q="اساتید">اساتید</button>' +
                '</div></div>';
            results.querySelectorAll('[data-q]').forEach(function (btn) {
                btn.addEventListener('click', function () {
                    input.value = btn.getAttribute('data-q') || '';
                    syncClear();
                    runSearch(input.value.trim());
                    input.focus();
                });
            });
        }

        function renderItems(items) {
            results.hidden = false;
            root.classList.add('is-open');
            results.innerHTML = items.map(function (item, idx) {
                var type = item.type || item.filter || 'page';
                var label = TYPE_LABEL[type] || TYPE_LABEL[item.filter] || 'نتیجه';
                return '<a class="site-search-hit" role="option" data-index="' + idx + '" href="' + escapeHtml(item.url) + '">' +
                    '<span class="site-search-badge ' + badgeClass(item.type, item.filter) + '">' + escapeHtml(label) + '</span>' +
                    '<span class="site-search-hit-title">' + escapeHtml(item.title) + '</span>' +
                    '<span class="site-search-hit-meta">' + escapeHtml(item.hint || '') + '</span>' +
                    '</a>';
            }).join('');
            activeIndex = -1;
        }

        function runSearch(q) {
            lastQ = q;
            if (!q) {
                hideResults();
                return;
            }
            var url = '/api/live-search/?q=' + encodeURIComponent(q) + '&filter=all';
            fetch(url, { credentials: 'same-origin' })
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (input.value.trim() !== lastQ) return;
                    var items = (data && data.results) || [];
                    if (!items.length) {
                        showEmpty();
                        return;
                    }
                    renderItems(items);
                })
                .catch(function () {
                    results.hidden = false;
                    root.classList.add('is-open');
                    results.innerHTML = '<div class="site-search-empty"><div class="site-search-empty-title">خطا در جستجو</div></div>';
                });
        }

        function moveActive(delta) {
            var hits = results.querySelectorAll('.site-search-hit');
            if (!hits.length) return;
            activeIndex = (activeIndex + delta + hits.length) % hits.length;
            hits.forEach(function (el, i) {
                el.classList.toggle('is-active', i === activeIndex);
            });
            hits[activeIndex].scrollIntoView({ block: 'nearest' });
        }

        input.addEventListener('input', function () {
            syncClear();
            clearTimeout(timer);
            var q = input.value.trim();
            timer = setTimeout(function () { runSearch(q); }, 200);
        });

        input.addEventListener('focus', function () {
            root.classList.add('is-open');
            if (input.value.trim()) runSearch(input.value.trim());
        });

        input.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                hideResults();
                input.blur();
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                moveActive(1);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                moveActive(-1);
            } else if (e.key === 'Enter') {
                var hits = results.querySelectorAll('.site-search-hit');
                if (activeIndex >= 0 && hits[activeIndex]) {
                    e.preventDefault();
                    window.location.href = hits[activeIndex].getAttribute('href');
                } else if (hits[0]) {
                    e.preventDefault();
                    window.location.href = hits[0].getAttribute('href');
                } else if (input.value.trim()) {
                    window.location.href = '/search/?q=' + encodeURIComponent(input.value.trim());
                }
            }
        });

        if (clearBtn) {
            clearBtn.addEventListener('click', function () {
                input.value = '';
                syncClear();
                hideResults();
                input.focus();
            });
        }

        document.addEventListener('click', function (e) {
            if (!e.target.closest('#siteTopSearch')) hideResults();
        });

        syncClear();
    }

    document.addEventListener('DOMContentLoaded', initSiteLiveSearch);
})();
