"""Pine Hollow background contract and native proxy checks."""
import unittest

import kiko
import make_kiko_art as art
from test_ridge_background import BackgroundChecks


class KikoBackgroundTests(BackgroundChecks, unittest.TestCase):
    contract = kiko
    art = art


if __name__ == "__main__":
    unittest.main()
