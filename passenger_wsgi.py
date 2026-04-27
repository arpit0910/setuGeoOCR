import os
import sys

# 1. CRITICAL: Limit threads BEFORE importing cv2 or numpy
# This prevents the "Resource temporarily unavailable" error
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["CV_NUM_THREADS"] = "1"

# 2. Add the project directory to path
sys.path.insert(0, os.path.dirname(__file__))

# 3. Import the bridge and your app
try:
    from a2wsgi import ASGIMiddleware
    from main import app
    application = ASGIMiddleware(app)
except Exception as e:
    # This will log the specific error if the import still fails
    with open(os.path.join(os.path.dirname(__file__), "error_debug.log"), "a") as f:
        f.write(f"Startup Error: {str(e)}\n")
    raise