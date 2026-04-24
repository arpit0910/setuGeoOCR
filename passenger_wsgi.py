import sys
import os

# Add the project directory to the sys.path
sys.path.insert(0, os.path.dirname(__file__))

from main import wsgi_app as application
