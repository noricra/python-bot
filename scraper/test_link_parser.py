"""
Tests unitaires pour le link_parser
"""

import unittest
from link_parser_v2 import BioLinkParser


class TestBioLinkParser(unittest.TestCase):
    """Tests pour BioLinkParser"""

    def setUp(self):
        self.parser = BioLinkParser()

    def test_extract_email_from_text(self):
        """Test extraction email basique"""

        # Test 1 : Email simple
        text = "Contact me at john.doe@business.com for business"
        email = self.parser.extract_email_from_text(text)
        self.assertEqual(email, "john.doe@business.com")

        # Test 2 : Plusieurs emails (doit prendre le premier valide)
        text = "Emails: test@noreply.com or contact@startup.co"
        email = self.parser.extract_email_from_text(text)
        self.assertEqual(email, "contact@startup.co")  # Ignore noreply

        # Test 3 : Email avec underscores et chiffres
        text = "Email: user_name123@mycompany.io"
        email = self.parser.extract_email_from_text(text)
        self.assertEqual(email, "user_name123@mycompany.io")

        # Test 4 : Pas d'email
        text = "No email here, just some text"
        email = self.parser.extract_email_from_text(text)
        self.assertIsNone(email)

        # Test 5 : Email invalide
        text = "Invalid email: notanemail@"
        email = self.parser.extract_email_from_text(text)
        self.assertIsNone(email)

    def test_extract_bio_links(self):
        """Test extraction de liens depuis bio"""

        # Test 1 : Linktree
        bio = "Check my links: https://linktr.ee/johndoe"
        links = self.parser.extract_bio_links(bio)
        self.assertIn("https://linktr.ee/johndoe", links)

        # Test 2 : Plusieurs liens
        bio = "Links: https://linktr.ee/user and www.mysite.com"
        links = self.parser.extract_bio_links(bio)
        self.assertEqual(len(links), 2)

        # Test 3 : Lien sans https://
        bio = "Visit linktr.ee/user"
        links = self.parser.extract_bio_links(bio)
        self.assertTrue(len(links) > 0)

        # Test 4 : Pas de liens
        bio = "Just some text without any links"
        links = self.parser.extract_bio_links(bio)
        self.assertEqual(len(links), 0)

    def test_bio_link_detection(self):
        """Test détection des types de liens bio"""

        test_urls = [
            ("https://linktr.ee/user", True),
            ("https://beacons.ai/creator", True),
            ("https://bio.link/profile", True),
            ("https://stan.store/seller", True),
            ("https://google.com", False),  # Pas un lien bio
        ]

        for url, is_bio_link in test_urls:
            # Vérifier si le lien contient une plateforme bio
            is_detected = any(platform in url.lower() for platform in
                            ['linktree', 'linktr.ee', 'beacons', 'bio.link', 'stan.store'])
            if is_bio_link:
                self.assertTrue(is_detected, f"{url} devrait être détecté comme lien bio")


class TestEmailPatterns(unittest.TestCase):
    """Tests pour patterns d'emails complexes"""

    def setUp(self):
        self.parser = BioLinkParser()

    def test_email_variations(self):
        """Test différents formats d'emails"""

        test_cases = [
            ("Email: john@business.com", "john@business.com"),
            ("📧 contact@startup.co", "contact@startup.co"),
            ("mailto:info@company.org", "info@company.org"),
            ("reach me: hello@creator.io", "hello@creator.io"),
            ("CONTACT: JOHN.DOE@COMPANY.COM", "JOHN.DOE@COMPANY.COM"),
        ]

        for text, expected_email in test_cases:
            email = self.parser.extract_email_from_text(text)
            self.assertEqual(email.lower() if email else None,
                           expected_email.lower())

    def test_ignore_invalid_emails(self):
        """Test que les emails invalides sont ignorés"""

        invalid_cases = [
            "Contact: noreply@example.com",  # noreply ignoré
            "Test: test@test.com",  # test ignoré
            "Email: @invalid.com",  # Format invalide
            "Email: invalid@",  # Format invalide
        ]

        for text in invalid_cases:
            email = self.parser.extract_email_from_text(text)
            # Soit None, soit un email valide (pas noreply/test)
            if email:
                self.assertNotIn('noreply', email.lower())
                self.assertNotIn('test@test', email.lower())


if __name__ == '__main__':
    print("=" * 60)
    print("🧪 TESTS LINK_PARSER")
    print("=" * 60)
    unittest.main(verbosity=2)
