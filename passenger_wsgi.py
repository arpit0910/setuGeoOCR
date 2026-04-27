import os
import sys
import asyncio

# 1. Thread limiting
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["CV_NUM_THREADS"] = "1"

# 2. Path setup
sys.path.insert(0, os.path.dirname(__file__))

# 3. Debug logging
log_path = os.path.join(os.path.dirname(__file__), "passenger_debug.log")

def log(msg):
    with open(log_path, "a") as f:
        f.write(f"{msg}\n")
        f.flush()

log(f"\n--- Process {os.getpid()} starting ---")

try:
    # Pre-initialize event loop
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    
    from a2wsgi import ASGIMiddleware
    from main import app
    
    # Create the bridge
    asgi_app = ASGIMiddleware(app)
    log("ASGI Bridge created.")

    # 4. Custom WSGI Wrapper to handle Root (/) directly as a fallback
    def application(environ, start_response):
        path = environ.get('PATH_INFO', '/')
        
        # If it's a root request, try to serve it directly to bypass ASGI bridge for diagnosis
        if path == '/' or path == '':
            log("Serving Root (/) via direct WSGI fallback")
            try:
                index_path = os.path.join(os.path.dirname(__file__), "index.html")
                with open(index_path, "rb") as f:
                    content = f.read()
                start_response('200 OK', [
                    ('Content-Type', 'text/html; charset=utf-8'),
                    ('Content-Length', str(len(content)))
                ])
                return [content]
            except Exception as e:
                log(f"Fallback failed: {e}")
        
        # For all other paths, use the ASGI bridge
        return asgi_app(environ, start_response)

    log("Application wrapper ready.")

except Exception as e:
    log(f"Initialization Error: {str(e)}")
    raise