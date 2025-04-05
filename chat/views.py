import os
import json
import requests
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from dotenv import load_dotenv
# from .LLM import chat_bot


# Load environment variables
load_dotenv()


# Chat view
def cheat(request):
    return render(request, 'chat/chat.html')

# Cheat API view
# @csrf_exempt
# def cheatapi(request):
#     try:
#         if request.method == "POST":
#             data = json.loads(request.body)
#             message = data.get('message')

#             print("Received Message:", message)  # ✅ Debug print

#             # Chat with the bot
#             response = chat_bot(message)
#             print("API Response:", response)  # ✅ Debug print
           
#             return JsonResponse({'response': response})
#     except Exception as error:
#         print("Error:", error)  
#         return JsonResponse({'error': str(error)})
