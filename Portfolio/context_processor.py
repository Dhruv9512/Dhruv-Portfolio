from django.shortcuts import render
from home.models import MyImage,Footer
from django.urls import reverse
# Create your views here.


# pass the header and footer data
def fotter_data(request):
    address_data = Footer.objects.filter(title="Address").first()
    mobile_data = Footer.objects.filter(title="Mobile Number").first()
    Email_data = Footer.objects.filter(title="Email").first()
    Footer_About_Me_Data = Footer.objects.filter(title="Footer About Me").first()
    logo_data = MyImage.objects.filter(title="Profile Logo").first()
    

    context = {
        "Image":{"Profile_Logo":logo_data},
        "Footer":{"Address":address_data,"Mobile_Number":mobile_data,"Email":Email_data,"about_me":Footer_About_Me_Data}
    }
    return context
