"""
Pytest configuration and fixtures for security tests.
"""

import os
import sys
import pytest
import tempfile
from pathlib import Path

# Ensure the project root is in the path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


# Custom markers
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "security: Security-related tests")
    config.addinivalue_line("markers", "slow: Slow tests (timing, etc.)")
    config.addinivalue_line("markers", "integration: Integration tests requiring full app")


@pytest.fixture
def temp_workdir():
    """Create a temporary work directory for file operations."""
    with tempfile.TemporaryDirectory(prefix="korev_test_") as tmpdir:
        # Create typical subdirectories
        (Path(tmpdir) / "uploads").mkdir()
        (Path(tmpdir) / "data").mkdir()
        yield Path(tmpdir)


@pytest.fixture
def sample_files(temp_workdir):
    """Create sample files for testing."""
    files = {}
    
    # Text file
    text_path = temp_workdir / "data" / "sample.txt"
    text_path.write_text("Hello, World!")
    files["text"] = text_path
    
    # JSON file
    json_path = temp_workdir / "data" / "config.json"
    json_path.write_text('{"key": "value"}')
    files["json"] = json_path
    
    # Create a nested structure
    nested = temp_workdir / "data" / "nested" / "deep"
    nested.mkdir(parents=True)
    (nested / "file.txt").write_text("Deep file")
    files["deep"] = nested / "file.txt"
    
    yield files


@pytest.fixture
def mock_env_vars():
    """Temporarily set environment variables for testing."""
    original = {}
    
    def _set_env(**kwargs):
        for key, value in kwargs.items():
            original[key] = os.environ.get(key)
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    
    yield _set_env
    
    # Restore original values
    for key, value in original.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.fixture
def clean_rate_limiters():
    """Reset rate limiters before and after test."""
    from python.security.rate_limit.limiter import reset_limiter
    
    # Reset to fresh limiter
    reset_limiter()
    
    yield
    
    # Reset again after test
    reset_limiter()


# Fixtures for Flask testing
@pytest.fixture
def app():
    """Create Flask test application."""
    try:
        # Import the actual Flask app
        import sys
        sys.path.insert(0, str(project_root))
        
        # This will be available after integration
        from run_ui import webapp
        
        webapp.config['TESTING'] = True
        webapp.config['WTF_CSRF_ENABLED'] = False
        
        yield webapp
    except ImportError:
        pytest.skip("Flask app not available for testing")


@pytest.fixture
def client(app):
    """Create Flask test client."""
    return app.test_client()
