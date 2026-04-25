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
    def application(environ, start_response):
        start_response('500 Internal Server Error', [('Content-Type', 'text/html')])
        exc_type, exc_value, exc_traceback = sys.exc_info()
        err_msg = traceback.format_exc()
        
        import config
        tess_path = config.TESSERACT_CMD
        tess_exists = os.path.exists(tess_path) if tess_path else False
        
        html = f"""
        <html>
            <head>
                <title>API Deployment Error</title>
                <style>
                    body {{ font-family: sans-serif; padding: 40px; background: #f8f9fa; color: #333; }}
                    .card {{ max-width: 900px; margin: auto; background: #fff; padding: 30px; border-radius: 12px; border: 1px solid #dee2e6; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
                    h1 {{ color: #dc3545; margin-top: 0; }}
                    pre {{ background: #212529; color: #f8f9fa; padding: 15px; overflow: auto; border-radius: 6px; font-size: 13px; line-height: 1.5; }}
                    .info-box {{ background: #e9ecef; padding: 15px; border-radius: 6px; margin-bottom: 20px; }}
                    .status {{ font-weight: bold; }}
                    .status-ok {{ color: #28a745; }}
                    .status-fail {{ color: #dc3545; }}
                </style>
            </head>
            <body>
                <div class="card">
                    <h1>FastAPI Boot Error</h1>
                    <p>Passenger failed to initialize the WSGI bridge. Below are diagnostic details to help you fix the issue.</p>
                    
                    <div class="info-box">
                        <p><strong>Python Executable:</strong> <code>{sys.executable}</code></p>
                        <p><strong>Project Root:</strong> <code>{PROJECT_ROOT}</code></p>
                        <p><strong>Tesseract Path:</strong> <code>{tess_path}</code> 
                           <span class="status {'status-ok' if tess_exists else 'status-fail'}">
                               ({'EXISTS' if tess_exists else 'NOT FOUND'})
                           </span>
                        </p>
                    </div>

                    <h3>Traceback</h3>
                    <pre>{err_msg}</pre>
                    
                    <hr/>
                    <h4>Troubleshooting Steps:</h4>
                    <ul>
                        <li>Verify that <strong>a2wsgi</strong> is installed: <code>pip install a2wsgi</code></li>
                        <li>Check if <strong>Tesseract OCR</strong> is installed on the server.</li>
                        <li>Ensure <strong>.env</strong> file does not contain Windows paths if running on Linux.</li>
                    </ul>
                </div>
            </body>
        </html>
        """
        return [html.encode('utf-8')]