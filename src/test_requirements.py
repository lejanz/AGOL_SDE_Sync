"""Test availability of required packages."""

import unittest
from pathlib import Path
from src.ui_functions import logging

import pkg_resources

_REQUIREMENTS_PATH = Path(__file__).parent.with_name("requirements.txt")


class TestRequirements(unittest.TestCase):
    """Test availability of required packages."""

    def test_requirements(self):
        """Test that each required package is available."""
        # Ref: https://stackoverflow.com/a/45474387/
        requirements = pkg_resources.parse_requirements(_REQUIREMENTS_PATH.open())
        success = True
        for requirement in requirements:
            requirement = str(requirement)
            with self.subTest(requirement=requirement):
                try:
                    pkg_resources.require(requirement)
                except Exception as e:
                    logging.error(e)
                    success = False

        if not success:
            exit()
