# Railway Deployment Guide - README

## 🚂 Railway Deployment for University Site

این branch برای deployment روی **Railway** آماده شده است.

### 📋 فایل‌های تنظیم

```
university_site/
├── config/settings.py          ⚙️ Settings برای Production
├── requirements.txt             📦 Dependencies کامل
├── Procfile                     📋 Railway configuration
├── build.sh                     🔨 Build script
├── runtime.txt                  🐍 Python version
├── .env.example                 📄 Environment variables
├── .gitignore                   🚫 Git ignore rules
└── RAILWAY_SETUP_STEPS.md       📚 Step-by-step guide (فارسی)
```

### 🚀 Quick Start

#### 1. ایجاد Railway Account
```
https://railway.app
```

#### 2. تنظیم PostgreSQL
```
Dashboard → + Add Service → PostgreSQL
```

#### 3. تنظیم Web Service
```
+ New Project → GitHub Repo → university-site
Branch: railway-deployment
Root Directory: university_site/
```

#### 4. Build & Start Commands
```bash
Build:  cd university_site && bash build.sh
Start:  cd university_site && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
```

#### 5. Environment Variables
```
SECRET_KEY=...
DEBUG=False
ALLOWED_HOSTS=your-app.railway.app
DATABASE_URL=... (auto from PostgreSQL)
EMAIL_HOST_USER=...
EMAIL_HOST_PASSWORD=...
```

#### 6. Deploy & Migrate
```bash
railway run python manage.py migrate
railway run python manage.py createsuperuser
```

### 📖 مراجع

- 📚 راهنمای کامل: `RAILWAY_SETUP_STEPS.md`
- 🔗 Railway Docs: https://docs.railway.app
- 🎯 Django Guide: https://docs.railway.app/guides/django

### ✅ Deployed?

```
https://your-app.railway.app
```

### 🔧 Troubleshooting

مشکل داشتید؟ راهنمای کامل را ببینید: `RAILWAY_SETUP_STEPS.md`

---

**Ready to deploy! 🚀**
