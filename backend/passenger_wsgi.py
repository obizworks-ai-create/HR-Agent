import os
import sys
from a2wsgi import ASGIMiddleware

# 1. Add current directory to sys.path so we can import 'main'
sys.path.insert(0, os.path.dirname(__file__))

# 2. Import the FastAPI 'app' from main.py
from main import app as asgi_app

# 3. Create the WSGI application adapter
# Phusion Passenger (cPanel) looks for 'application' by default
application = ASGIMiddleware(asgi_app)
