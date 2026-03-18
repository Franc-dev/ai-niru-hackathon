import unittest

from backend.services.guardrails import check_guardrail, is_off_topic


class GuardrailTests(unittest.TestCase):
    def test_blocks_typoed_python_request(self):
        message = "pls help me codein python"

        self.assertTrue(is_off_topic(message))
        should_redirect, redirect = check_guardrail(message, "en")
        self.assertTrue(should_redirect)
        self.assertIn("mental health", redirect)

    def test_blocks_explicit_python_request(self):
        message = "please help me code in python"

        self.assertTrue(is_off_topic(message))
        should_redirect, redirect = check_guardrail(message, "en")
        self.assertTrue(should_redirect)
        self.assertIn("not with programming", redirect)

    def test_allows_emotional_support_about_python_assignment(self):
        message = "i am stressed about my python assignment"

        self.assertFalse(is_off_topic(message))
        self.assertEqual(check_guardrail(message, "en"), (False, None))

    def test_allows_anxiety_message_with_programming_context(self):
        message = "python is making me anxious"

        self.assertFalse(is_off_topic(message))
        self.assertEqual(check_guardrail(message, "en"), (False, None))


if __name__ == "__main__":
    unittest.main()
