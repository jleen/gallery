import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from gallery import app


def application(a, b): return app.application(a, b)
