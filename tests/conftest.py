# ============================================================================
# FabAssetsManager - Test Configuration
# ============================================================================
# Description: Shared pytest fixtures and configuration for FabAssetsManager tests.
# Version: 1.0.3
# ============================================================================

import warnings
import pytest
import app


@pytest.fixture
def client():
    app.app.config['TESTING'] = True
    with app.app.test_client() as client:
        yield client


# Silence an environment-level warning emitted by langsmith on Python 3.14+.
warnings.filterwarnings(
    "ignore",
    message="Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater.",
    category=UserWarning,
    module=r"langsmith\.schemas",
)
