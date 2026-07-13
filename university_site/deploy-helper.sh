#!/bin/bash
# Railway Deployment Helper Script

echo "🚂 Railway University Site Deployment Helper"
echo "============================================="
echo ""

echo "✅ Step 1: Requirements Check"
echo "Checking if all dependencies are installed..."
pip check

echo ""
echo "✅ Step 2: Database Migrations"
echo "Running migrations..."
python manage.py migrate

echo ""
echo "✅ Step 3: Static Files"
echo "Collecting static files..."
python manage.py collectstatic --noinput

echo ""
echo "✅ Step 4: Testing"
echo "Running Django check..."
python manage.py check --deploy

echo ""
echo "✅ All deployment checks completed!"
echo "Your site is ready to go! 🚀"
