# Allameh Amini Higher Education Institute

[![Django](https://img.shields.io/badge/Django-5.2-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5_RTL-7952B3?logo=bootstrap&logoColor=white)](https://getbootstrap.com/)
[![License](https://img.shields.io/badge/License-Proprietary-lightgrey)](#license)

Official institutional website and academic portal for **Allameh Amini Higher Education Institute (Behnamir)** — a full-stack Persian (RTL) platform for admissions, academics, research, and student services.

**Repository path:** `university_site/`

---

## Overview

This project delivers a production-oriented university web presence with:

- A public marketing & information site (Persian RTL UI)
- Online admissions with SMS OTP verification
- Role-based academic dashboards (student / professor / staff / admin)
- CMS-style content management via Django Admin (Jazzmin)
- SMS notifications (Kavenegar) for key academic events
- Tuition calculator and student list export (Excel / Word)

Built for real institutional workflows — not a static brochure site.

---

## Key Features

### Public website
- Responsive RTL layout (Vazirmatn), AOS animations, homepage hero slider
- Academic groups, majors, departments, faculty profiles
- News, announcements, events, gallery
- Research hub (projects, theses, conferences, journals)
- Digital library, FAQ, e-services, city / institution pages
- Contact forms and industry partnership flows

### Admissions
- Unified online application for associate → PhD tracks
- Mobile OTP verification (Kavenegar)
- Application tracking by national ID / tracking code
- Tuition information and interactive tuition calculator
- Staff tools for reviewing and updating application status (with SMS alerts)

### Academic portal
- Student dashboard: courses, grades, requests, assignments, exams, payments
- Professor dashboard: teaching assignments, grading, submissions
- Staff / university manager tools: request handling, student export by major
- Editable student profiles with major linkage

### Operations & integrations
- Jazzmin admin with Persian RTL enhancements
- Role-synced staff permissions (`مدیر دانشگاه` group)
- Kavenegar SMS: OTP + event notifications (admission status, enrollment, profile, announcements/news)
- Payment gateway abstraction (`mock` for development, Zarinpal-ready for production)
- SQLite / PostgreSQL / MySQL support via environment configuration

---

## Tech Stack

| Layer | Technology |
|--------|------------|
| Backend | Django 5.2 |
| Frontend | Bootstrap 5 RTL, Font Awesome, AOS, custom CSS/JS |
| Admin | django-jazzmin |
| Forms | django-crispy-forms + Bootstrap 5 |
| Dates | jdatetime (Jalali) |
| SMS | Kavenegar API |
| Export | openpyxl, python-docx |
| Config | python-decouple (`.env`) |

---

## Project Structure

```text
university_site/
├── config/           # Django settings (dev / prod)
├── core/             # Home, site settings, pages, SMS client, notifications
├── accounts/         # Auth, profiles, staff permissions, OTP reset
├── admissions/       # Applications, tuition, OTP admissions flow
├── academics/        # Departments, majors, courses, calendar
├── faculty/          # Professors & publications
├── research/         # Research content & industry partnerships
├── library/          # Digital library
├── news/             # News, categories, gallery
├── contact/          # Contact & alumni
├── dashboard/        # Role-based panels + student export
├── templates/        # HTML templates
├── static/           # CSS, JS, images
├── locale/           # Persian translations
└── requirements.txt
```

---

## Quick Start

### Prerequisites
- Python 3.11+ recommended
- `pip` and a virtual environment

### Setup

```bash
cd university_site
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # Windows
# cp .env.example .env  # macOS / Linux
```

Edit `.env` and set at least:

```env
SECRET_KEY=your-long-random-secret
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DB_ENGINE=sqlite
```

Then:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

| URL | Purpose |
|-----|---------|
| http://127.0.0.1:8000/ | Public site |
| http://127.0.0.1:8000/admin/ | Admin panel |
| http://127.0.0.1:8000/dashboard/ | Academic portal |

> Never commit real secrets. Keep `.env` local only (`.env.example` is the template).

---

## Environment Configuration

Important variables (see `.env.example` for the full list):

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | Development mode flag |
| `ALLOWED_HOSTS` | Host allow-list |
| `DB_ENGINE` | `sqlite` \| `postgres` \| `mysql` |
| `SMS_ENABLED` | Enable live Kavenegar sending |
| `KAVENEGAR_API_KEY` | Kavenegar API key |
| `KAVENEGAR_OTP_TEMPLATE` | Verify/lookup template name (recommended for OTP) |
| `SMS_SENDER_NUMBER` | Sender line for plain SMS notifications |
| `SMS_SITE_LABEL` | Prefix used in notification messages |
| `PAYMENT_GATEWAY` | `mock` or `zarinpal` |
| `ZARINPAL_MERCHANT_ID` | Required when using Zarinpal |

### SMS notes
- Trial Kavenegar accounts may only deliver to the account owner’s phone (`HTTP 501`).
- For production OTP, configure an approved **verify template** and set `KAVENEGAR_OTP_TEMPLATE`.
- Event notifications use plain SMS (`sms/send`) and typically need an active account + sender line.

Test command:

```bash
python manage.py test_kavenegar 09xxxxxxxxx
```

---

## Roles

| Role | Access |
|------|--------|
| Student | Dashboard courses, grades, requests, payments |
| Professor | Teaching, grading, assignment review |
| Staff (university manager) | Limited admin modules + student export + request handling |
| Admin | Full Django admin / superuser |

Staff permissions are managed through `accounts/staff_permissions.py` and kept in sync with profile role changes.

---

## Student Export

Staff and admins can filter registered students by degree/major and download:

- **Excel** (`.xlsx`)
- **Word** (`.docx`)

Path: `/dashboard/staff/students/export/`

Assign each student’s **Major** in Admin → Profiles for accurate filtering.

---

## Deployment

Production guidance lives in:

- `university_site/DEPLOYMENT_GUIDE.md`
- `university_site/SUBDOMAIN_DEPLOYMENT.md`

Typical production checklist:

1. Set `DEBUG=False` and secure `SECRET_KEY`
2. Configure `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS`
3. Use PostgreSQL or MySQL
4. Collect static files and configure media storage
5. Enable HTTPS cookies / HSTS as documented
6. Turn on SMS and payment credentials only in production secrets

---

## Development Scripts

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_aab_features      # optional demo/content seeding
python manage.py setup_staff_access    # sync university-manager group
python manage.py test_kavenegar 09...  # SMS connectivity check
python manage.py runserver
```

---

## Roadmap Ideas

- Official Ministry of Science (SAORG / Sitad–PGSB) degree verification API after institutional onboarding
- Student self-service course registration UI
- Richer payment reconciliation and receipts
- Automated CI (lint, tests, deploy)

---

## Contributing

1. Create a feature branch from `main`
2. Keep commits focused and descriptive
3. Do not commit `.env`, credentials, or local media dumps
4. Open a pull request with a clear summary and test notes

---

## License

Proprietary — All rights reserved for Allameh Amini Higher Education Institute (Behnamir), unless otherwise agreed in writing.

---

## Contact

- Institution: Allameh Amini Higher Education Institute, Behnamir, Mazandaran, Iran
- Repository: [github.com/Davoadeivai/university-site](https://github.com/Davoadeivai/university-site)

---

<p align="center">
  <sub>Built with Django · Designed for Persian higher education workflows</sub>
</p>
