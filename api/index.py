import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, init_db, db

with app.app_context():
    try:
        init_db()
    except Exception as e:
        print(f"Warning: Could not initialize DB: {e}")

def handler(request):
    with app.app_context():
        return app.wsgi_app(request.environ, request.start_response)
