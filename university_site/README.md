# Allameh Amini Higher Education Institute — Application

This folder contains the Django application.

For the full project documentation (features, setup, SMS, deployment), see the repository root:

**[../README.md](../README.md)**

```bash
cd university_site
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
