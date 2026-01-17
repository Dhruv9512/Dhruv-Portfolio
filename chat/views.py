import os
import json
import requests
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from dotenv import load_dotenv

# Change Import: Import the class instead of the global graph variable
from .LLM import MyChatbot 

# Load environment variables
load_dotenv()

# Chat view
def cheat(request):
    return render(request, 'chat/chat.html')

# Cheat API view
@csrf_exempt
def cheatapi(request):
    try:
        if request.method == "POST":
            data = json.loads(request.body)
            message = data.get('message')
            thread_id = data.get('thread_id')

            # 1. Setup Config
            config = {
                "configurable": {"thread_id": str(thread_id)}
            }

            # 2. Instantiate and Run MyChatbot
            bot = MyChatbot(message=message, config=config)
            response = bot.build()

            # 3. Extract Response Content
            last_message_content = response["messages"][-1].content
            
            # 4. Parse JSON Payload (to separate display text from memory)
            try:
                parsed_payload = json.loads(last_message_content)
                final_display_text = parsed_payload.get('content', last_message_content)
            except (json.JSONDecodeError, TypeError):
                final_display_text = last_message_content

            return JsonResponse({'response': final_display_text})
            
    except Exception as error:
        print("Error:", error)  
        return JsonResponse({'error': str(error)})