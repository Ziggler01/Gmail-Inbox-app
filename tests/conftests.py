# tests/conftest.py
import sys
from pathlib import Path

# Add repo root to sys.path so `import app` works in tests
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
