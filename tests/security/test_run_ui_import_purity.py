"""
Import Purity Test: run_ui.py without litellm

This test proves that `import run_ui` and `create_app()` do NOT trigger
imports of litellm, models, or initialize modules.

CRITICAL INVARIANT:
- E2E tests for /login must run WITHOUT litellm installed
- CI should be able to test login flow without LLM dependencies
- Any violation means someone reintroduced heavy imports at module level

This test will FAIL if:
- `import run_ui` triggers `import litellm`
- `create_app()` triggers `import initialize`
- Any module-level import cascades to LLM dependencies
"""

import os
import sys
import subprocess
import pytest


class TestRunUiImportPurity:
    """
    Tests that run_ui.py can be imported without LLM dependencies.
    
    These tests use subprocess isolation to ensure clean import state.
    """
    
    @pytest.mark.security
    def test_import_run_ui_without_litellm(self):
        """
        Importing run_ui should NOT import litellm.
        
        This test runs in a subprocess to ensure clean import state.
        """
        code = '''
import sys

# Block litellm import - will raise if anyone tries to import it
class LiteLLMBlocker:
    def find_module(self, name, path=None):
        if name == 'litellm' or name.startswith('litellm.'):
            return self
        return None
    
    def load_module(self, name):
        raise ImportError(f"BLOCKED: {name} import attempted - run_ui should not import litellm!")

sys.meta_path.insert(0, LiteLLMBlocker())

# Now try to import run_ui
try:
    import run_ui
    print("SUCCESS: run_ui imported without litellm")
    sys.exit(0)
except ImportError as e:
    if "litellm" in str(e).lower():
        print(f"FAILED: litellm import was triggered: {e}")
        sys.exit(1)
    else:
        # Other import error - reraise
        raise
'''
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            env={**os.environ, "PYTHONPATH": os.path.dirname(os.path.dirname(os.path.dirname(__file__)))},
        )
        
        if result.returncode != 0:
            pytest.fail(
                f"run_ui.py imports litellm at module level!\n"
                f"stdout: {result.stdout}\n"
                f"stderr: {result.stderr}"
            )
    
    @pytest.mark.security
    def test_import_run_ui_without_initialize(self):
        """
        Importing run_ui should NOT import initialize module.
        
        The initialize module cascades to models which cascades to litellm.
        """
        code = '''
import sys

# Block initialize import
class InitializeBlocker:
    def find_module(self, name, path=None):
        if name == 'initialize':
            return self
        return None
    
    def load_module(self, name):
        raise ImportError(f"BLOCKED: {name} import attempted - run_ui should not import initialize!")

sys.meta_path.insert(0, InitializeBlocker())

# Now try to import run_ui
try:
    import run_ui
    print("SUCCESS: run_ui imported without initialize")
    sys.exit(0)
except ImportError as e:
    if "initialize" in str(e).lower():
        print(f"FAILED: initialize import was triggered: {e}")
        sys.exit(1)
    else:
        raise
'''
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            env={**os.environ, "PYTHONPATH": os.path.dirname(os.path.dirname(os.path.dirname(__file__)))},
        )
        
        if result.returncode != 0:
            pytest.fail(
                f"run_ui.py imports initialize at module level!\n"
                f"stdout: {result.stdout}\n"
                f"stderr: {result.stderr}"
            )
    
    @pytest.mark.security
    def test_import_run_ui_without_models(self):
        """
        Importing run_ui should NOT import models module.
        
        The models module directly imports litellm.
        """
        code = '''
import sys

# Block models import
class ModelsBlocker:
    def find_module(self, name, path=None):
        if name == 'models':
            return self
        return None
    
    def load_module(self, name):
        raise ImportError(f"BLOCKED: {name} import attempted - run_ui should not import models!")

sys.meta_path.insert(0, ModelsBlocker())

try:
    import run_ui
    print("SUCCESS: run_ui imported without models")
    sys.exit(0)
except ImportError as e:
    if "models" in str(e).lower():
        print(f"FAILED: models import was triggered: {e}")
        sys.exit(1)
    else:
        raise
'''
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            env={**os.environ, "PYTHONPATH": os.path.dirname(os.path.dirname(os.path.dirname(__file__)))},
        )
        
        if result.returncode != 0:
            pytest.fail(
                f"run_ui.py imports models at module level!\n"
                f"stdout: {result.stdout}\n"
                f"stderr: {result.stderr}"
            )
    
    @pytest.mark.security
    def test_create_app_without_litellm(self):
        """
        create_app() should work without litellm installed.
        
        This is the critical test for E2E login tests in CI.
        """
        code = '''
import sys
import os

# Set test environment
os.environ["AUTH_LOGIN"] = "test"
os.environ["AUTH_PASSWORD"] = "test"
os.environ["KOREV_PRODUCTION"] = "false"

# Block litellm
class LiteLLMBlocker:
    def find_module(self, name, path=None):
        if name == 'litellm' or name.startswith('litellm.'):
            return self
        return None
    
    def load_module(self, name):
        raise ImportError(f"BLOCKED: {name} import attempted!")

sys.meta_path.insert(0, LiteLLMBlocker())

# Import and call create_app
from run_ui import create_app
app = create_app(testing=True)

# Verify app is functional
assert app is not None
assert hasattr(app, 'test_client')

# Quick smoke test - get login page
with app.test_client() as client:
    response = client.get('/login')
    assert response.status_code == 200

print("SUCCESS: create_app() works without litellm")
sys.exit(0)
'''
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            env={**os.environ, "PYTHONPATH": os.path.dirname(os.path.dirname(os.path.dirname(__file__)))},
        )
        
        if result.returncode != 0:
            pytest.fail(
                f"create_app() requires litellm!\n"
                f"stdout: {result.stdout}\n"
                f"stderr: {result.stderr}"
            )
    
    @pytest.mark.security
    def test_login_endpoint_without_litellm(self):
        """
        /login endpoint should work without litellm.
        
        This is the full E2E smoke test for login in CI.
        """
        code = '''
import sys
import os

# Set test environment
os.environ["AUTH_LOGIN"] = "testuser"
os.environ["AUTH_PASSWORD"] = "testpass"
os.environ["KOREV_PRODUCTION"] = "false"
os.environ["KOREV_RATE_LIMIT_BACKEND"] = "memory"

# Block litellm
class LiteLLMBlocker:
    def find_module(self, name, path=None):
        if name == 'litellm' or name.startswith('litellm.'):
            return self
        return None
    
    def load_module(self, name):
        raise ImportError(f"BLOCKED: {name}")

sys.meta_path.insert(0, LiteLLMBlocker())

from run_ui import create_app
app = create_app(testing=True)

with app.test_client() as client:
    # GET /login
    response = client.get('/login')
    assert response.status_code == 200, f"GET /login failed: {response.status_code}"
    
    # POST /login with wrong credentials
    response = client.post('/login', data={'username': 'wrong', 'password': 'wrong'})
    assert response.status_code == 200, f"POST /login (invalid) failed: {response.status_code}"
    
    # POST /login with correct credentials
    response = client.post('/login', data={'username': 'testuser', 'password': 'testpass'}, follow_redirects=False)
    assert response.status_code == 302, f"POST /login (valid) should redirect: {response.status_code}"

print("SUCCESS: /login works without litellm")
sys.exit(0)
'''
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            env={**os.environ, "PYTHONPATH": os.path.dirname(os.path.dirname(os.path.dirname(__file__)))},
        )
        
        if result.returncode != 0:
            pytest.fail(
                f"/login endpoint requires litellm!\n"
                f"stdout: {result.stdout}\n"
                f"stderr: {result.stderr}"
            )


class TestModuleLevelImportCheck:
    """
    In-process tests to verify no litellm imports at module level.
    
    These tests check sys.modules after importing run_ui.
    """
    
    @pytest.mark.security
    def test_litellm_not_in_sys_modules_after_import(self):
        """
        After importing run_ui, litellm should NOT be in sys.modules.
        
        Note: This test may pass even if litellm was imported elsewhere.
        The subprocess tests above are more reliable.
        """
        # Save current state
        litellm_was_imported = 'litellm' in sys.modules
        
        if not litellm_was_imported:
            # Fresh import test
            import run_ui
            
            # Check if litellm was imported as a side effect
            # Note: This check is imperfect if litellm was already imported by another test
            if 'litellm' in sys.modules:
                # Only fail if we can confirm it wasn't there before
                pytest.fail(
                    "litellm was imported as a side effect of importing run_ui. "
                    "Check module-level imports in run_ui.py"
                )
    
    @pytest.mark.security
    def test_create_app_does_not_call_init_a0(self):
        """
        create_app() should NOT call init_a0().
        
        init_a0() imports initialize which imports litellm.
        """
        from unittest.mock import patch
        import run_ui
        
        with patch.object(run_ui, 'init_a0') as mock_init:
            app = run_ui.create_app(testing=True)
            
            # init_a0 should NOT have been called
            mock_init.assert_not_called()
            
            # App should still be valid
            assert app is not None
