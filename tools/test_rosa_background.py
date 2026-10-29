"""Signal Hill background contract and native proxy checks."""
import unittest

import make_rosa_art as art
import rosa
from test_ridge_background import BackgroundChecks


class RosaBackgroundTests(BackgroundChecks, unittest.TestCase):
    contract = rosa
    art = art


if __name__ == "__main__":
    unittest.main()
