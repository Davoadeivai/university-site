# Database Connection Troubleshooting

## PostgreSQL Connection Issues

### Error: could not translate host name
```bash
# Check DATABASE_URL format
echo $DATABASE_URL

# Should be:
# postgresql://user:password@host:port/dbname
```

### Error: Connection refused
```bash
# Verify PostgreSQL is running
# Check port 5432 is open
# Verify credentials are correct
```

### Error: role "postgres" does not exist
```bash
# Create user first
# Or use different user
```

## Email Configuration

### Gmail Issues
```
1. Enable 2FA: https://myaccount.google.com/security
2. Get App Password: https://myaccount.google.com/apppasswords
3. Use 16-char password (without spaces)
4. Don't use main password
```

## Static Files

### 404 on CSS/JS
```bash
python manage.py collectstatic --noinput
```

### Whitenoise not working
```python
# Check MIDDLEWARE order
# SecurityMiddleware must be BEFORE WhiteNoiseMiddleware
```

## Debug Mode

### Temporarily enable DEBUG
```bash
# In Railway Variables:
DEBUG=True

# Then redeploy
# Check logs for detailed errors
# Turn OFF after fixing!
```

## Logs

### View Railway Logs
```bash
railway logs

# Or in Dashboard:
# Deployments → View Logs
```

## Restart Service

```bash
# Via Railway CLI
railway redeploy

# Or manually via Dashboard:
# Deployments → Redeploy
```

---

**Need help? Check RAILWAY_SETUP_STEPS.md**
