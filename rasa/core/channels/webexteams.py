import logging
from sanic import Blueprint, response
from typing import Text, Optional, Dict, Any
from webexteamssdk import WebexTeamsAPI, Webhook

from rasa.core.channels import InputChannel
from rasa.core.channels.channel import UserMessage, OutputChannel

logger = logging.getLogger(__name__)


class WebexTeamsBot(OutputChannel):
    """A Cisco WebexTeams communication channel."""

    @classmethod
    def name(cls):
        return "webexteams"

    def __init__(self, access_token, room):
        self.room = room
        self.api = WebexTeamsAPI(access_token)

    async def send_text_message(self, recipient_id, message):
        recipient = self.room or recipient_id
        for message_part in message.split("\n\n"):
            self.api.messages.create(roomId=recipient, text=message_part)

    async def send_image_url(self, recipient_id, image_url):
        recipient = self.room or recipient_id
        return self.api.messages.create(roomId=recipient, files=[image_url])

    async def send_file_url(self, recipient_id, file_url):
        recipient = self.room or recipient_id
        return self.api.messages.create(roomId=recipient, files=[file_url])

    async def send_custom_json(self, recipient_id, kwargs: Dict[Text, Any]):
        kwargs.setdefault("roomID", recipient_id)
        return self.api.messages.create(**kwargs)


class WebexTeamsInput(InputChannel):
    """WebexTeams input channel. Based on the HTTPInputChannel."""

    @classmethod
    def name(cls):
        return "webexteams"

    @classmethod
    def from_credentials(cls, credentials):
        if not credentials:
            cls.raise_missing_credentials_exception()

        return cls(credentials.get("access_token"), credentials.get("room"))

    def __init__(self, access_token: Text, room: Optional[Text] = None) -> None:
        """Create a Cisco Webex Teams input channel.

        Needs a couple of settings to properly authenticate and validate
        messages. Details here https://developer.webex.com/authentication.html

        Args:
            access_token: Cisco WebexTeams bot access token.
            room: the string identifier for a room to which the bot posts
        """
        self.token = access_token
        self.room = room
        self.api = WebexTeamsAPI(access_token)

    async def process_message(self, on_new_message, text, sender_id):

        try:
            out_channel = WebexTeamsBot(self.token, self.room)
            user_msg = UserMessage(
                text, out_channel, sender_id, input_channel=self.name()
            )
            await on_new_message(user_msg)
        except Exception as e:
            logger.error("Exception when trying to handle message.{0}".format(e))
            logger.error(str(e), exc_info=True)

    def blueprint(self, on_new_message):
        webexteams_webhook = Blueprint("webexteams_webhook", __name__)

        @webexteams_webhook.route("/", methods=["GET"])
        async def health(request):
            return response.json({"status": "ok"})

        @webexteams_webhook.route("/webhook", methods=["POST"])
        async def webhook(request):
            """Respond to inbound webhook HTTP POST from Webex Teams."""

            logger.debug("Received webex webhook call")
            # Get the POST data sent from Webex Teams
            json_data = request.json

            # Create a Webhook object from the JSON data
            webhook_obj = Webhook(json_data)
            # Get the message details
            message = self.api.messages.get(webhook_obj.data.id)

            # This is a VERY IMPORTANT loop prevention control step.
            # If you respond to all messages...  You will respond to the
            # messages that the bot posts and thereby create a loop
            me = self.api.people.me()
            if message.personId == me.id:
                # Message was sent by me (bot); do not respond.
                return response.text("OK")

            else:
                await self.process_message(
                    on_new_message, text=message.text, sender_id=message.personId
                )
                return response.text("")

        return webexteams_webhook
