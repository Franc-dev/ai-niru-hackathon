import unittest
from unittest.mock import AsyncMock, patch

from backend.api.v1.endpoints import chat as chat_endpoint
from backend.api.v1.endpoints.chat import ChatRequest
from backend.services.agent import agent_service
from backend.services.intent_router import route_message
from backend.services.recommendations import recommendation_service


class RecommendationFocusTests(unittest.TestCase):
    def test_incomplete_self_harm_phrase_uses_crisis_dataset_response(self):
        response = recommendation_service.maybe_build_response(
            message="i want to kill",
            history=[],
            language="en",
        )

        self.assertIsNotNone(response)
        self.assertEqual(response["metadata"]["recommendation_kind"], "crisis")
        self.assertTrue(response["metadata"]["cards"])

    def test_history_follow_up_for_sadness_does_not_force_counselor_cards(self):
        history = [{"role": "user", "content": "I feel very sad"}]

        response = recommendation_service.maybe_build_response(
            message="can i get book a counselor please",
            history=history,
            language="en",
        )

        self.assertIsNone(response)

    def test_explicit_depression_can_still_match_depression_support(self):
        history = [{"role": "user", "content": "I think I am depressed"}]

        response = recommendation_service.maybe_build_response(
            message="find a counselor please",
            history=history,
            language="en",
        )

        self.assertIsNotNone(response)
        self.assertEqual(response["metadata"]["recommendation_topic"], "depression")
        self.assertTrue(
            any("Depression" in str(card.get("description", "")) for card in response["metadata"]["cards"])
        )

    def test_router_detects_sadness_not_depression_for_mild_language(self):
        route = route_message(
            message="I feel very sad",
            history=[],
            language="en",
        )

        self.assertEqual(route.intent, "emotional_support")
        self.assertIn("Detected focus: sadness", route.prompt_context)
        self.assertNotIn("Detected focus: depression", route.prompt_context)

    def test_router_keeps_counselor_request_without_blind_counselor_recommendation(self):
        route = route_message(
            message="can i get book a counselor please",
            history=[{"role": "user", "content": "I feel very sad"}],
            language="en",
        )

        self.assertEqual(route.intent, "counselor_request")
        self.assertIsNone(route.recommendation)
        self.assertIsNotNone(route.fallback_reply)
        self.assertTrue(route.fallback_reply["metadata"]["request_unavailable"])
        self.assertEqual(route.fallback_reply["metadata"]["request_kind"], "counselor")
        self.assertEqual(route.fallback_reply["metadata"]["recommendation_focus_label"], "sadness")
        self.assertTrue(route.fallback_reply["text"].strip())

    def test_router_marks_crisis_when_phrase_matches_dataset_backed_detection(self):
        route = route_message(
            message="I want to end my life",
            history=[],
            language="en",
        )

        self.assertEqual(route.intent, "crisis")
        self.assertIsNotNone(route.recommendation)
        self.assertEqual(route.recommendation["metadata"]["recommendation_kind"], "crisis")
        self.assertTrue(route.recommendation["metadata"]["cards"])

    def test_generic_counselor_request_gets_direct_unavailable_reply(self):
        route = route_message(
            message="i need a counselor",
            history=[],
            language="en",
        )

        self.assertEqual(route.intent, "counselor_request")
        self.assertIsNone(route.recommendation)
        self.assertIsNotNone(route.fallback_reply)
        self.assertTrue(route.fallback_reply["metadata"]["request_unavailable"])
        self.assertEqual(route.fallback_reply["metadata"]["request_kind"], "counselor")
        self.assertTrue(route.fallback_reply["text"].strip())

    def test_current_message_topic_overrides_old_history(self):
        history = [{"role": "user", "content": "I feel very sad"}]

        response = recommendation_service.maybe_build_response(
            message="show me resources for sleep",
            history=history,
            language="en",
        )

        self.assertIsNotNone(response)
        self.assertEqual(response["metadata"]["recommendation_kind"], "resources")
        self.assertEqual(response["metadata"]["recommendation_topic"], "sleep")
        self.assertEqual(response["metadata"]["recommendation_reason"], "current_message")


class ChatEndpointHistoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_chat_endpoint_routes_incomplete_self_harm_phrase_to_crisis_cards(self):
        stored_messages = []

        async def fake_get_or_create_conversation(user_id, conversation_id=None, language="en"):
            return conversation_id or "conv-1"

        async def fake_add_message(conversation_id, role, content, metadata=None):
            stored_messages.append(
                {
                    "message_id": str(len(stored_messages) + 1),
                    "role": role,
                    "content": content,
                    "metadata": metadata or {},
                    "timestamp": "2026-03-15T00:00:00+00:00",
                }
            )
            return stored_messages[-1]["message_id"]

        async def fake_get_conversation_messages(conversation_id):
            return [dict(message) for message in stored_messages]

        async def fake_get_conversation(conversation_id, user_id):
            return {
                "conversation_id": conversation_id,
                "title": None,
                "language": "en",
            }

        with (
            patch.object(chat_endpoint, "get_or_create_conversation", new=fake_get_or_create_conversation),
            patch.object(chat_endpoint, "add_message", new=fake_add_message),
            patch.object(chat_endpoint, "get_conversation_messages", new=fake_get_conversation_messages),
            patch.object(chat_endpoint, "get_conversation", new=fake_get_conversation),
            patch.object(chat_endpoint, "set_conversation_title_if_empty", new=AsyncMock(return_value=True)),
            patch.object(chat_endpoint, "update_conversation_language", new=AsyncMock(return_value=True)),
            patch.object(chat_endpoint, "update_user_preferred_language", new=AsyncMock(return_value=True)),
            patch.object(chat_endpoint, "check_safety_rules", return_value={"safe": True}),
        ):
            response = await chat_endpoint.chat(
                ChatRequest(message="i want to kill"),
                current_user={"id": "user-1", "preferred_language": "en"},
            )

        self.assertTrue(response.response.strip())
        self.assertEqual(response.message_metadata["recommendation_kind"], "crisis")
        self.assertTrue(response.message_metadata["cards"])

    async def test_chat_endpoint_returns_unavailable_reply_when_no_counselor_match_exists(self):
        stored_messages = []

        async def fake_get_or_create_conversation(user_id, conversation_id=None, language="en"):
            return conversation_id or "conv-1"

        async def fake_add_message(conversation_id, role, content, metadata=None):
            stored_messages.append(
                {
                    "message_id": str(len(stored_messages) + 1),
                    "role": role,
                    "content": content,
                    "metadata": metadata or {},
                    "timestamp": "2026-03-15T00:00:00+00:00",
                }
            )
            return stored_messages[-1]["message_id"]

        async def fake_get_conversation_messages(conversation_id):
            return [dict(message) for message in stored_messages]

        async def fake_get_conversation(conversation_id, user_id):
            return {
                "conversation_id": conversation_id,
                "title": None,
                "language": "en",
            }

        with (
            patch.object(chat_endpoint, "get_or_create_conversation", new=fake_get_or_create_conversation),
            patch.object(chat_endpoint, "add_message", new=fake_add_message),
            patch.object(chat_endpoint, "get_conversation_messages", new=fake_get_conversation_messages),
            patch.object(chat_endpoint, "get_conversation", new=fake_get_conversation),
            patch.object(chat_endpoint, "set_conversation_title_if_empty", new=AsyncMock(return_value=True)),
            patch.object(chat_endpoint, "update_conversation_language", new=AsyncMock(return_value=True)),
            patch.object(chat_endpoint, "update_user_preferred_language", new=AsyncMock(return_value=True)),
            patch.object(chat_endpoint, "check_safety_rules", return_value={"safe": True}),
        ):
            await chat_endpoint.chat(
                ChatRequest(message="I feel very sad"),
                current_user={"id": "user-1", "preferred_language": "en"},
            )
            response = await chat_endpoint.chat(
                ChatRequest(
                    message="can i get book a counselor please",
                    conversation_id="conv-1",
                ),
                current_user={"id": "user-1", "preferred_language": "en"},
            )

        self.assertTrue(response.response.strip())
        self.assertTrue(response.message_metadata["request_unavailable"])
        self.assertEqual(response.message_metadata["request_kind"], "counselor")
        self.assertEqual(response.message_metadata["recommendation_focus_label"], "sadness")

    async def test_agent_returns_direct_unavailable_reply_for_generic_counselor_request(self):
        reply = await agent_service.process_message(
            "i need a counselor",
            "conv-1",
            [],
            language="en",
        )

        self.assertTrue(reply.text.strip())
        self.assertEqual(reply.metadata["request_kind"], "counselor")
        self.assertTrue(reply.metadata["request_unavailable"])


if __name__ == "__main__":
    unittest.main()
