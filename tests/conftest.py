"""FabAssetsManager — Test Configuration

Version: 0.13.5
"""

import sys
import warnings
from pathlib import Path

# Add the root project directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Silence an environment-level warning emitted by langsmith on Python 3.14+.
warnings.filterwarnings(
    "ignore",
    message="Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater.",
    category=UserWarning,
    module=r"langsmith\.schemas",
)
