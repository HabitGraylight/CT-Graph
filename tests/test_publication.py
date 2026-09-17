import unittest
from scripts.check_publication import allowed_path, SECRET


class PublicationTests(unittest.TestCase):
    def test_private_paths_cannot_be_authorized_by_manifest(self):
        for name in ('data/personal/recipe.md', 'output/menu.md', 'tmp/request.json',
                     'tests/cache.sqlite', 'docs/.env', '../secret.md', 'web/menu.pdf'):
            self.assertFalse(allowed_path(name, [name]), name)

    def test_new_paths_default_private(self):
        self.assertTrue(allowed_path('docs/PRIVACY.md', ['docs/PRIVACY.md']))
        self.assertFalse(allowed_path('docs/private-notes.md', ['docs/PRIVACY.md']))

    def test_common_credential_detected(self):
        self.assertIsNotNone(SECRET.search(b'ghp_' + b'x' * 36))


if __name__ == '__main__':
    unittest.main()
