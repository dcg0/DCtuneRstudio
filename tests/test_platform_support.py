import unittest

from platform_support import RuntimePlatform


class PlatformSupportTests(unittest.TestCase):
    def test_x86_64_windows_is_supported(self):
        self.assertTrue(RuntimePlatform("Windows", "AMD64", 64).supported)

    def test_x86_64_linux_is_supported(self):
        self.assertTrue(RuntimePlatform("Linux", "x86_64", 64).supported)

    def test_32_bit_is_not_supported(self):
        self.assertFalse(RuntimePlatform("Linux", "x86_64", 32).supported)


if __name__ == "__main__":
    unittest.main()
