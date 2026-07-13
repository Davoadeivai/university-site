// ============================================================
//  دانشگاه جامع - اسکریپت اصلی
// ============================================================

document.addEventListener('DOMContentLoaded', function () {

    // ---- AOS Init ----
    if (typeof AOS !== 'undefined') {
        AOS.init({ duration: 700, once: true, easing: 'ease-out-cubic', offset: 60 });
    }

    // ---- Navbar Scroll Effect ----
    const navbar = document.getElementById('mainNav');
    if (navbar) {
        window.addEventListener('scroll', function () {
            if (window.scrollY > 60) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
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

    // ---- Hero Swiper ----
    if (document.querySelector('.hero-swiper')) {
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
                const target = parseInt(el.getAttribute('data-target'));
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

    // ---- Search Autocomplete Placeholder ----
    const searchInput = document.querySelector('.search-input');
    if (searchInput) {
        const placeholders = ['جستجوی اخبار...', 'جستجوی اساتید...', 'جستجوی رشته‌ها...', 'جستجوی خدمات...'];
        let pi = 0;
        setInterval(function () {
            pi = (pi + 1) % placeholders.length;
            searchInput.placeholder = placeholders[pi];
        }, 2500);
    }

    // ---- Gallery Lightbox ----
    const galleryItems = document.querySelectorAll('.gallery-item');
    galleryItems.forEach(function (item) {
        item.addEventListener('click', function () {
            const imgSrc = item.querySelector('img') ? item.querySelector('img').src : '';
            if (imgSrc) {
                const modal = document.createElement('div');
                modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.92);z-index:9999;display:flex;align-items:center;justify-content:center;cursor:zoom-out;';
                modal.innerHTML = `<img src="${imgSrc}" style="max-width:90vw;max-height:90vh;border-radius:12px;box-shadow:0 20px 60px rgba(0,0,0,0.5);">`;
                modal.addEventListener('click', function () { document.body.removeChild(modal); });
                document.body.appendChild(modal);
            }
        });
    });

    // ---- Active Nav Link ----
    const currentPath = window.location.pathname;
    document.querySelectorAll('.nav-link').forEach(function (link) {
        if (link.getAttribute('href') && link.getAttribute('href') !== '#' &&
            currentPath.startsWith(link.getAttribute('href')) && link.getAttribute('href') !== '/') {
            link.classList.add('active');
        }
    });

    // ---- Ticker ----
    const tickers = document.querySelectorAll('.urgent-ticker');
    tickers.forEach(function (ticker) {
        const content = ticker.innerHTML;
        ticker.innerHTML = content + ' &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ' + content;
        let pos = 0;
        setInterval(function () {
            pos -= 1;
            if (pos < -ticker.scrollWidth / 2) pos = 0;
            ticker.style.transform = `translateX(${pos}px)`;
        }, 20);
    });

});

// ---- Chatbot Toggle ----
function toggleChatbot() {
    const widget = document.getElementById('chatbotWidget');
    if (widget) {
        widget.style.display = widget.style.display === 'none' ? 'block' : 'none';
    }
}

// ---- Chatbot Responses ----
const chatResponses = {
    'پذیرش': 'برای پذیرش دانشجو می‌توانید از بخش پذیرش در منوی اصلی اقدام کنید. <a href="/پذیرش/">کلیک کنید</a>',
    'رشته': 'رشته‌های متعددی در مقاطع کاردانی، کارشناسی و ارشد داریم. <a href="/آموزش/رشته‌ها/">مشاهده رشته‌ها</a>',
    'شهریه': 'اطلاعات شهریه در بخش پذیرش موجود است. <a href="/پذیرش/">مشاهده</a>',
    'اساتید': 'لیست اعضای هیئت علمی: <a href="/اساتید/">مشاهده اساتید</a>',
    'تماس': 'می‌توانید از طریق فرم تماس با ما در ارتباط باشید: <a href="/تماس-با-ما/">تماس با ما</a>',
    'کتابخانه': 'به کتابخانه دیجیتال ما خوش آمدید: <a href="/کتابخانه/">کتابخانه</a>',
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
            if (msg.includes(key)) { resp = chatResponses[key]; break; }
        }
        appendMsg(resp, 'bot');
    }, 700);
}

function sendQuickMsg(msg) {
    document.getElementById('chatInput').value = msg;
    sendMsg();
}

function appendMsg(text, type) {
    const container = document.getElementById('chatMessages');
    if (!container) return;
    const div = document.createElement('div');
    div.className = `chat-msg ${type === 'user' ? 'user-msg' : ''}`;
    div.innerHTML = type === 'bot'
        ? `<i class="fas fa-robot"></i><div class="msg-bubble">${text}</div>`
        : `<i class="fas fa-user"></i><div class="msg-bubble">${text}</div>`;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

// ---- Site Tour (Intro.js) ----
function startSiteTour() {
    if (typeof introJs === 'undefined') return;
    introJs().setOptions({
        nextLabel: 'بعدی ›',
        prevLabel: '‹ قبلی',
        skipLabel: '✕ بستن',
        doneLabel: '✓ اتمام',
        buttonClass: 'introjs-button',
        steps: [
            {
                title: '🏫 به سایت خوش آمدید',
                intro: 'این راهنما شما را با بخش‌های اصلی سایت آموزش عالی آشنا می‌کند.'
            },
            {
                element: document.querySelector('.navbar-brand'),
                title: '🎓 لوگوی مؤسسه',
                intro: 'برای بازگشت به صفحه اصلی روی لوگو کلیک کنید.'
            },
            {
                element: document.querySelector('#mainNav .navbar-nav'),
                title: '📋 منوی اصلی',
                intro: 'از این منو می‌توانید به تمام بخش‌های سایت دسترسی داشته باشید: آموزش، اساتید، کتابخانه، پذیرش و تماس.'
            },
            {
                element: document.querySelector('.search-form'),
                title: '🔍 جستجوی هوشمند',
                intro: 'از کادر جستجو برای یافتن اخبار، رشته‌های تحصیلی، اساتید و خدمات استفاده کنید.'
            },
            {
                element: document.querySelector('.quick-link-card'),
                title: '⚡ دسترسی سریع',
                intro: 'این آیکون‌ها دسترسی سریع به خدمات پراستفاده مانند سامانه آموزشی، پذیرش، کتابخانه و تقویم را فراهم می‌کنند.'
            },
            {
                element: document.querySelector('#chatbotBtn'),
                title: '🤖 دستیار هوشمند',
                intro: 'برای پرسش سریع درباره پذیرش، رشته‌ها و خدمات، روی این دکمه کلیک کنید و با دستیار هوشمند صحبت نمایید.'
            }
        ]
    }).start();
}

document.addEventListener('DOMContentLoaded', function () {
    const tourBtn = document.getElementById('startSiteTour');
    if (tourBtn) {
        tourBtn.addEventListener('click', startSiteTour);
    }
});

