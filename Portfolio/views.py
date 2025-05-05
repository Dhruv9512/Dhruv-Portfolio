from django.http import JsonResponse

# View for pinging the app
def ping(request):
    return JsonResponse({"status": "ok", "message": "The app is alive!"})
