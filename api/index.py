import sys
import os
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, init_db

_db_initialized = False
_init_lock = threading.Lock()


def ensure_database_ready():
    global _db_initialized
    if _db_initialized:
        return
    with _init_lock:
        if _db_initialized:
            return
        try:
            init_db()
            _db_initialized = True
        except Exception as e:
            print(f"DB Init Error: {e}")
            raise


def handler(request):
    ensure_database_ready()
    with app.app_context():
        return app.wsgi_app(request.environ, request.start_response)
