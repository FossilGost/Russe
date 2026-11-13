"""Performance changes must retain safe dependency updates and cache behavior."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.check_dependencies import ready


class LauncherTests(unittest.TestCase):
    def test_launcher_rechecks_changed_requirements_before_skipping_pip(self):
        with tempfile.TemporaryDirectory() as folder:
            lock=Path(folder)/'requirements.lock'
            requirements=Path(folder)/'requirements.txt'
            lock.write_text('example==1.2.3\n',encoding='utf-8')
            with patch('scripts.check_dependencies.version',return_value='1.2.3'):
                requirements.write_text('example>=1.2,<2\n',encoding='utf-8')
                self.assertTrue(ready(lock,requirements))
                requirements.write_text('example>=2,<3\n',encoding='utf-8')
                self.assertFalse(ready(lock,requirements))
                requirements.write_text('example~=1.2\n',encoding='utf-8')
                self.assertFalse(ready(lock,requirements))
            with patch('scripts.check_dependencies.version',return_value='1.2.2'):
                self.assertFalse(ready(lock))
