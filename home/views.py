from django.shortcuts import render
from .models import MyImage,Footer,File
# Create your views here.
def home(request):
    image_data = MyImage.objects.filter(title="Profile Photo").first()
    resume_data = File.objects.filter(title="Resume").first()
    context = {
        "home_Image":{"profile_photo":image_data , "Resume":resume_data},
    }
    return render(request, 'home/home.html',context)