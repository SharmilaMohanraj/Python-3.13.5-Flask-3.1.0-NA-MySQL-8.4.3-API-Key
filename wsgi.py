"""WSGI entry point for gunicorn/waitress: `gunicorn wsgi:app` / `waitress-serve --port=8000 wsgi:app`."""
from app import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
