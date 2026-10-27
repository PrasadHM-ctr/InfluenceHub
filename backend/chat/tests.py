from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from businesses.models import BusinessProfile
from campaigns.models import CampaignRequest
from influencers.models import InfluencerProfile

from .models import Conversation, Message


TEST_CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
TEST_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "chat-tests",
    }
}


@override_settings(CHANNEL_LAYERS=TEST_CHANNEL_LAYERS, CACHES=TEST_CACHES)
class ChatApiTests(APITestCase):
    def setUp(self):
        self.business_user = User.objects.create_user(username="brand", password="safe-password-123")
        self.influencer_user = User.objects.create_user(username="creator", password="safe-password-123")
        self.outsider_user = User.objects.create_user(username="outsider", password="safe-password-123")
        self.business = BusinessProfile.objects.create(
            user=self.business_user,
            company_name="Brand Co",
            industry="Technology",
            phone="1234567890",
            city="Mumbai",
            state="Maharashtra",
        )
        self.influencer = InfluencerProfile.objects.create(
            user=self.influencer_user,
            full_name="Creator One",
            category="Tech",
            language="English",
            followers=10000,
            city="Delhi",
            state="Delhi",
        )
        self.accepted_campaign = CampaignRequest.objects.create(
            business=self.business,
            influencer=self.influencer,
            title="Accepted campaign",
            message="A campaign ready for chat.",
            budget="10000.00",
            status="Accepted",
        )
        self.pending_campaign = CampaignRequest.objects.create(
            business=self.business,
            influencer=self.influencer,
            title="Pending campaign",
            message="A campaign without chat.",
            budget="8000.00",
            status="Pending",
        )
        self.conversation = Conversation.objects.get(campaign=self.accepted_campaign)

    def test_only_accepted_campaign_participants_can_open_chat(self):
        self.client.force_authenticate(self.business_user)
        conversations = self.client.get("/api/chat/conversations/")
        self.assertEqual(conversations.status_code, status.HTTP_200_OK)
        self.assertEqual(conversations.data[0]["id"], self.conversation.id)

        started = self.client.post("/api/chat/start/", {"campaign_id": self.accepted_campaign.id}, format="json")
        self.assertEqual(started.status_code, status.HTTP_200_OK)
        self.assertEqual(started.data["id"], self.conversation.id)

        pending = self.client.post("/api/chat/start/", {"campaign_id": self.pending_campaign.id}, format="json")
        self.assertEqual(pending.status_code, status.HTTP_400_BAD_REQUEST)

        self.client.force_authenticate(self.outsider_user)
        forbidden = self.client.get(f"/api/chat/messages/{self.conversation.id}/")
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)

    def test_messages_are_marked_read_and_file_uploads_are_delivered(self):
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.influencer_user,
            text="Hello from the creator",
        )
        self.client.force_authenticate(self.business_user)
        response = self.client.get(f"/api/chat/messages/{self.conversation.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["messages"][0]["text"], message.text)
        message.refresh_from_db()
        self.assertTrue(message.is_read)

        uploaded_file = SimpleUploadedFile(
            "brief.pdf",
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 0>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF",
            content_type="application/pdf",
        )
        upload = self.client.post(
            "/api/chat/upload/",
            {"conversation": self.conversation.id, "file": uploaded_file},
            format="multipart",
        )
        self.assertEqual(upload.status_code, status.HTTP_201_CREATED)
        uploaded_message = Message.objects.get(id=upload.data["id"])
        self.addCleanup(uploaded_message.file.delete, False)
        self.assertIn(".pdf", upload.data["file_url"])


@override_settings(CHANNEL_LAYERS=TEST_CHANNEL_LAYERS, CACHES=TEST_CACHES)
class ChatWebSocketTests(APITestCase):
    def setUp(self):
        self.business_user = User.objects.create_user(username="business-ws", password="safe-password-123")
        self.influencer_user = User.objects.create_user(username="creator-ws", password="safe-password-123")
        business = BusinessProfile.objects.create(
            user=self.business_user,
            company_name="WebSocket Brand",
            industry="Lifestyle",
            phone="1234567890",
            city="Mumbai",
            state="Maharashtra",
        )
        influencer = InfluencerProfile.objects.create(
            user=self.influencer_user,
            full_name="WebSocket Creator",
            category="Lifestyle",
            language="English",
            followers=9000,
            city="Pune",
            state="Maharashtra",
        )
        campaign = CampaignRequest.objects.create(
            business=business,
            influencer=influencer,
            title="WebSocket campaign",
            message="Chat testing campaign.",
            budget="12000.00",
            status="Accepted",
        )
        self.conversation = Conversation.objects.get(campaign=campaign)

    def test_authenticated_participants_exchange_events_and_unauthorized_user_is_rejected(self):
        async_to_sync(self._run_websocket_test)()

    async def _run_websocket_test(self):
        from config.asgi import application

        business_token = f"fake.{self.business_user.pk}.token"
        influencer_token = f"fake.{self.influencer_user.pk}.token"
        business = WebsocketCommunicator(
            application,
            f"/ws/chat/{self.conversation.id}/?token={business_token}",
            headers=[(b"origin", b"http://localhost:3000")],
        )
        influencer = WebsocketCommunicator(
            application,
            f"/ws/chat/{self.conversation.id}/?token={influencer_token}",
            headers=[(b"origin", b"http://localhost:3000")],
        )
        connected, _ = await business.connect()
        self.assertTrue(connected)
        await business.receive_json_from()

        connected, _ = await influencer.connect()
        self.assertTrue(connected)
        await influencer.receive_json_from()
        await business.receive_json_from()

        await business.send_json_to({"type": "message", "text": "Hello in real time"})
        business_event = await business.receive_json_from()
        influencer_event = await influencer.receive_json_from()
        self.assertEqual(business_event["type"], "message")
        self.assertEqual(influencer_event["message"]["text"], "Hello in real time")

        await business.send_json_to({"type": "typing", "is_typing": True})
        typing_event = await influencer.receive_json_from()
        self.assertEqual(typing_event, {"type": "typing", "user_id": self.business_user.id, "is_typing": True})

        await influencer.send_json_to({"type": "read", "message_ids": [business_event["message"]["id"]]})
        receipt = await business.receive_json_from()
        self.assertEqual(receipt["type"], "read_receipt")
        self.assertIn(business_event["message"]["id"], receipt["message_ids"])

        await business.disconnect()
        await influencer.disconnect()

        intruder = WebsocketCommunicator(
            application,
            f"/ws/chat/{self.conversation.id}/",
            headers=[(b"origin", b"http://localhost:3000")],
        )
        connected, close_code = await intruder.connect()
        self.assertFalse(connected)
        self.assertEqual(close_code, 4403)
