import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .LLM import MyChatbot

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.thread_id = self.scope['url_route']['kwargs']['thread_id']
        
        self.room_group_name = f"chat_{self.thread_id}"
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get('message')
        thread_id = self.thread_id

        config = {"configurable": {"thread_id": str(thread_id)}}
        bot = MyChatbot(message=message, config=config)
        try:
            async for event in bot.build():
                if event["type"] == "token":
                    await self.send(text_data=json.dumps(event))
                elif event["type"] == "log":
                    await self.send(text_data=json.dumps(event))
                elif event["type"] == "done":
                    await self.send(text_data=json.dumps(event)) 
                    break
        except Exception as e:
            await self.send(text_data=json.dumps({"type": "error", "content": str(e)}))