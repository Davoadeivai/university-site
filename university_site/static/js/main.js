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
    const observerOptions = { threshold: 0.5 };
    const counterObserver = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
            if (entry.isIntersecting) {
                const el = entry.target;
                const target = parseInt(el.getAttribute('data-target'), 10);
                const duration = 2000;
                const step = target / (duration / 16);
                let current = 0;
                const timer = setInterval(function () {
                    current += step;
                    if (current >= target) {
                        current = target;
                        clearInterval(timer);
                    }
                    el.textContent = Math.floor(current).toLocaleString('fa-IR');
                }, 16);
                counterObserver.unobserve(el);
            }
        });
    }, observerOptions);
    counters.forEach(function (counter) { counterObserver.observe(counter); });

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

// ---- Site Tour (Intro.js) ----
function startSiteTour() {
    if (typeof introJs === 'undefined') return;
    const steps = [
        {
            title: 'به سایت خوش آمدید',
            intro: 'این راهنما شما را با بخش‌های اصلی سایت آموزش عالی آشنا می‌کند.'
        }
    ];
    const nav = document.querySelector('#mainNav .navbar-nav');
    if (nav) {
        steps.push({
            element: nav,
            title: 'منوی اصلی',
            intro: 'از این منو می‌توانید به تمام بخش‌های سایت دسترسی داشته باشید.'
        });
    }
    const quick = document.querySelector('.quick-link-card');
    if (quick) {
        steps.push({
            element: quick,
            title: 'دسترسی سریع',
            intro: 'این آیکون‌ها دسترسی سریع به خدمات پراستفاده را فراهم می‌کنند.'
        });
    }
    const chatBtn = document.querySelector('#chatbotBtn');
    if (chatBtn) {
        steps.push({
            element: chatBtn,
            title: 'دستیار هوشمند',
            intro: 'برای پرسش سریع درباره پذیرش، رشته‌ها و خدمات، روی این دکمه کلیک کنید.'
        });
    }
    introJs().setOptions({
        nextLabel: 'بعدی ›',
        prevLabel: '‹ قبلی',
        skipLabel: '✕ بستن',
        doneLabel: '✓ اتمام',
        buttonClass: 'introjs-button',
        steps: steps
    }).start();
}

document.addEventListener('DOMContentLoaded', function () {
    const tourBtn = document.getElementById('startSiteTour');
    if (tourBtn) {
        tourBtn.addEventListener('click', startSiteTour);
    }
});
