import os
import json
import requests
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from dotenv import load_dotenv
from .LLM import main_graph
from langchain.schema import HumanMessage


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


            # Chat with the bot

            config = {
                "configurable":{"thread_id":"1"}
            }
            response=main_graph.invoke(
                {"messages": HumanMessage(content=message)},
                config=config
            )
           
            return JsonResponse({'response': response["messages"][-1].content})
    except Exception as error:
        print("Error:", error)  
        return JsonResponse({'error': str(error)})
