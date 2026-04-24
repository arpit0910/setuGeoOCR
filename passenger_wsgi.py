import os
import sys
import traceback

# 1. Define paths
PROJECT_ROOT = os.path.dirname(__file__)
sys.path.insert(0, PROJECT_ROOT)

# 2. Entry Point
try:
    # We import 'wsgi_app' from main.py because Passenger is a WSGI server
    # and FastAPI is an ASGI app. The a2wsgi middleware bridges them.
    from main import wsgi_app as application

except Exception:
    # DEBUG MODE: If the app fails to load, show the traceback in the browser.
    # This prevents the generic "SORRY!" page and helps you debug missing libs.
    def application(environ, start_response):
        start_response('500 Internal Server Error', [('Content-Type', 'text/html')])
        exc_type, exc_value, exc_traceback = sys.exc_info()
        err_msg = traceback.format_exc()
        
        html = f"""
        <html>
            <head><title>API Deployment Error</title></head>
            <body style="font-family: sans-serif; padding: 40px; background: #f8f9fa;">
                <div style="max-width: 800px; margin: auto; background: #fff; padding: 20px; border-radius: 8px; border: 1px solid #dee2e6;">
                    <h1 style="color: #dc3545;">FastAPI Boot Error</h1>
                    <p>Passenger failed to initialize the WSGI bridge. This is likely due to a missing library or environment variable.</p>
                    <hr/>
                    <pre style="background: #212529; color: #f8f9fa; padding: 15px; overflow: auto; border-radius: 4px;">{err_msg}</pre>
                    <p style="font-size: 0.9em; color: #6c757d;">Check: <code>pip install a2wsgi fastapi uvicorn</code></p>
                </div>
            </body>
        </html>
        """
        return [html.encode('utf-8')]