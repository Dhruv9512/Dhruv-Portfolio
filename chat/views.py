import os
import json
import requests
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Hugging Face API key
HF_API_KEY = os.getenv('HUGGINGFACE_API_KEY')
if not HF_API_KEY:
    raise ValueError("HUGGINGFACE_API_KEY environment variable is not set.")

# Hugging Face API URL
MODEL_NAME = "HuggingFaceH4/zephyr-7b-beta"  # Change to any free model
API_URL = f"https://api-inference.huggingface.co/models/{MODEL_NAME}"

HEADERS = {
    "Authorization": f"Bearer {HF_API_KEY}",
    "Content-Type": "application/json"
}

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

            print("Received Message:", message)  # ✅ Debug print

            # Prepare the request payload
            payload = {"inputs": message}

            # Call Hugging Face API
            response = requests.post(API_URL, headers=HEADERS, json=payload)
            print("API Response:", response.text)  # ✅ Debug print
            if response.status_code == 200:
                result = response.json()
                generated_text = result[0]['generated_text']  # Extract response text
                return JsonResponse({'response': generated_text})
            else:
                return JsonResponse({'error': f"API Error: {response.text}"})

    except Exception as error:
        print("Error:", error)  
        return JsonResponse({'error': str(error)})
