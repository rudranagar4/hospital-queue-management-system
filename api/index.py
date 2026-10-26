import sys
import os

# Add project root directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app

class VercelPathFixMiddleware:
    """
    WSGI Middleware to adapt Vercel serverless function routing.
    Vercel rewrites forward requests to /api/index with the original route in HTTP_X_MATCHED_PATH.
    This middleware restores the original requested path into PATH_INFO so Flask routes properly.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        matched = environ.get('HTTP_X_MATCHED_PATH')
        if matched and not matched.startswith('/api/index'):
            environ['PATH_INFO'] = matched
        elif environ.get('PATH_INFO', '') == '/api/index':
            environ['PATH_INFO'] = '/'
        elif environ.get('PATH_INFO', '').startswith('/api/index/'):
            environ['PATH_INFO'] = environ['PATH_INFO'][len('/api/index'):]
        return self.wsgi_app(environ, start_response)

app.wsgi_app = VercelPathFixMiddleware(app.wsgi_app)
