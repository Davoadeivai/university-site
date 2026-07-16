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
                const image = document.createElement('img');
                const closeModal = function () {
                    if (modal.parentNode) document.body.removeChild(modal);
                    document.removeEventListener('keydown', onKeyDown);
                };
                const onKeyDown = function (event) {
                    if (event.key === 'Escape') closeModal();
                };
                modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.92);z-index:9999;display:flex;align-items:center;justify-content:center;cursor:zoom-out;';
                modal.setAttribute('role', 'dialog');
                modal.setAttribute('aria-label', 'نمایش بزرگ تصویر');
                image.src = imgSrc;
                image.alt = item.querySelector('img').alt;
                image.style.cssText = 'max-width:90vw;max-height:90vh;border-radius:12px;box-shadow:0 20px 60px rgba(0,0,0,0.5);';
                modal.appendChild(image);
                modal.addEventListener('click', closeModal);
                document.addEventListener('keydown', onKeyDown);
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
    'پذیرش': 'برای پذیرش دانشجو به بخش پذیرش در منوی اصلی مراجعه کنید.',
    'رشته': 'فهرست رشته‌ها در بخش آموزش در دسترس است.',
    'شهریه': 'اطلاعات شهریه در بخش پذیرش موجود است.',
    'اساتید': 'فهرست اعضای هیئت علمی در بخش اساتید در دسترس است.',
    'تماس': 'می‌توانید از طریق فرم «تماس با ما» با دانشگاه در ارتباط باشید.',
    'کتابخانه': 'کتابخانه دیجیتال از منوی اصلی قابل دسترسی است.',
    'default': 'برای راهنمایی، از منوی اصلی یا گزینه‌های پیشنهادی استفاده کنید.'
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
    const icon = document.createElement('i');
    const bubble = document.createElement('div');
    icon.className = type === 'bot' ? 'fas fa-robot' : 'fas fa-user';
    bubble.className = 'msg-bubble';
    bubble.textContent = text;
    div.append(icon, bubble);
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

