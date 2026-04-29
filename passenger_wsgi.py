import os
import sys
import logging

# 1. Environment & Thread Configuration
# --------------------------------------------------------------------------
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["CV_NUM_THREADS"] = "1"

# 2. Path Setup
# --------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# 3. Application Setup
# --------------------------------------------------------------------------
try:
    from a2wsgi import ASGIMiddleware
    from main import app
    
    # Create the WSGI application
    # a2wsgi handles the asyncio event loop management internally
    application = ASGIMiddleware(app)
    
except Exception as e:
    # Fallback to a very simple WSGI app if the main app fails to load
    # This prevents the "never ending loader" by at least returning an error
    def application(environ, start_response):
        status = '500 Internal Server Error'
        output = f"Internal Server Error during startup: {str(e)}".encode('utf-8')
        response_headers = [('Content-type', 'text/plain'),
                            ('Content-Length', str(len(output)))]
        start_response(status, response_headers)
        return [output]