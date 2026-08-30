# Backend production deployment

This checklist is provider-neutral. Choose a host that supports a Python WSGI
service, PostgreSQL, HTTPS, and either S3 or persistent filesystem volumes.

## 1. Environment

Copy `.env.production.example` to the production host as `.env` and replace all
placeholders. Generate `DJANGO_SECRET_KEY` separately; do not reuse a password
or commit the generated value.

``` powershell
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Set the real backend and frontend HTTPS origins. `DJANGO_ALLOWED_HOSTS` contains
host names only, while CORS/CSRF values and `FRONTEND_BASE_URL` contain full
`https://` origins. Enable `DJANGO_BEHIND_HTTPS_PROXY` only when the platform's
trusted reverse proxy terminates TLS and sends `X-Forwarded-Proto` correctly.

The production database must be PostgreSQL. SQLite is only for local testing.
Create a dedicated database user and restrict its network access to the backend
service.

## 2. File storage

Use S3 (`DJANGO_USE_S3=true`) on an ephemeral host. If S3 is disabled, mount
persistent volumes at both of these locations:

- `backend/media` for uploaded and generated images
- `backend/staticfiles` for collected static assets

The reverse proxy must serve `/media/` and `/static/` from those volumes. Django
and Gunicorn do not serve them in production.

## 3. Install, validate, and initialize

Run these commands from `backend` in the release environment:

``` sh
python -m pip install -r requirements.txt
python manage.py check_deployment_config
python manage.py check --deploy
python manage.py check_external_services
python manage.py migrate --noinput
python manage.py loaddata detect/fixtures/model_classes.json
python manage.py collectstatic --noinput
```

When persistent local volumes were deliberately mounted, run the first command
with `--allow-local-storage`. This option confirms the operator decision; it
does not create or verify the volumes.

Run external provider calls as a separate smoke test after deployment:

``` sh
python manage.py check_external_services --live kakao soil fertilizer weather market
```

## 4. Start and health check

Run the WSGI application with the platform-provided `PORT` value. Adjust worker
count and timeout after measuring memory use, especially when YOLO is enabled.

``` sh
gunicorn aivle_big.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120
```

After startup, verify `GET /api/capabilities/`, authentication email delivery,
one authenticated community write, and one request for every enabled external
service. Keep `CHATBOT_ENABLED=false` until a reviewed source CSV and matching
Chroma index have been installed.

## 5. Rollback and operations

Back up PostgreSQL and persistent media before schema changes. Keep the previous
application image/release available for rollback. Application logs must go to
standard output and must never include API keys, SMTP app passwords, session
cookies, or request authorization headers.
