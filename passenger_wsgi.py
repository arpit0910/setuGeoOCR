import os
import sys

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
with open(log_path, "a") as f:
    f.write(f"\n--- Process {os.getpid()} starting ---\n")
    f.write(f"Python: {sys.executable}\n")
    f.write(f"CWD: {os.getcwd()}\n")
    f.flush()

try:
    import asyncio
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    from a2wsgi import ASGIMiddleware
    from main import app
    application = ASGIMiddleware(app)
    
    with open(log_path, "a") as f:
        f.write("Application initialized successfully.\n")
except Exception as e:
    with open(log_path, "a") as f:
        f.write(f"Initialization Error: {str(e)}\n")
    raise