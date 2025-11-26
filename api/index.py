import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

def handler(request):
    with app.app_context():
        return app.wsgi_app(request.environ, request.start_response)

app = app
