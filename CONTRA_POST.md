# Contra Project Post — Copy & Paste

**Cover image:** `assets/contra-university-portal-cover.png`  
(Also mirrored under Cursor project assets — upload this as your Contra project cover.)

---

## Project title
Higher Education Web Platform — Admissions, Portal & SMS Ops

## One-liner (subtitle)
Full-stack Django portal for an Iranian higher-ed institute: RTL public site, OTP admissions, role-based dashboards, and automated SMS workflows.

## Skills / tags (add on Contra)
Django · Python · Bootstrap · RTL UI · REST/SMS APIs · PostgreSQL/MySQL · Jazzmin Admin · Product Engineering · EdTech

## Project URL
https://github.com/Davoadeivai/university-site

---

## Post body (paste into Contra description)

### The brief
Build more than a brochure website — deliver an operational platform for **Allameh Amini Higher Education Institute (Behnamir)** covering public content, online admissions, academic dashboards, and day-to-day staff workflows in a fully Persian RTL experience.

### What I shipped
- **Public institutional site** — responsive RTL UI (Bootstrap 5 + Vazirmatn), departments/majors, faculty, news, research, library, and e-services
- **Online admissions** — unified application flow (associate → PhD), mobile OTP via Kavenegar, tracking codes, tuition calculator
- **Role-based portal** — student / professor / staff / admin dashboards (courses, grades, requests, grading, payments)
- **Operations tooling** — Jazzmin admin, staff permission groups, Excel/Word student export by major
- **Event SMS notifications** — admission status, enrollment, profile updates, announcements/news (Kavenegar)
- **Production-ready config** — `.env`-driven settings, SQLite/Postgres/MySQL, Zarinpal-ready payments (mock in dev)

### Approach
I treated this as product engineering, not page templating:
1. Mapped real institutional journeys (apply → track → enroll → notify)
2. Built modular Django apps (`admissions`, `dashboard`, `accounts`, `core`, …)
3. Hardened auth/roles so staff get limited admin scope, not superuser by default
4. Integrated SMS with clear OTP vs notification paths and rate limits
5. Documented setup and ops in a professional English README for handoff

### Outcome
A cohesive EdTech platform ready for institutional use: branded public presence, measurable admissions funnel, staff tooling, and automated communication — with a clean GitHub README and deployable Django architecture.

### Stack
Django 5.2 · Python · Bootstrap 5 RTL · Jazzmin · Kavenegar · openpyxl / python-docx · python-decouple

---

## Short Contra “Work” blurb (if character-limited)

Designed and built a full Django higher-education platform: Persian RTL site, OTP admissions, student/professor portals, staff export tools, and Kavenegar SMS alerts — production-oriented, not a static brochure.

---

## Suggested Contra settings
- **Visibility:** Public
- **Category:** Software / Web Development / Product
- **Availability CTA:** Open to similar EdTech / institutional web platforms
- **Cover:** Upload `contra-university-portal-cover.png` (16:9)
