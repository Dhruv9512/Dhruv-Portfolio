from django.shortcuts import render
from home.models import MyImage,Footer
from django.urls import reverse
# Create your views here.


# pass the header and footer data
def fotter_data(request):
    # Get current year
    from datetime import datetime
    current_year = datetime.now().year

    # Footer details
    address_data = Footer.objects.filter(title="Address").first()
    mobile_data = Footer.objects.filter(title="Mobile Number").first()
    Email_data = Footer.objects.filter(title="Email").first()
    Footer_About_Me_Data = Footer.objects.filter(title="Footer About Me").first()
    leetcode_link = Footer.objects.filter(title="Leetcode").first()
    hackerrank_link = Footer.objects.filter(title="Hackerrank").first()
    linkedin_link = Footer.objects.filter(title="Linkedin").first()
    github_link = Footer.objects.filter(title="Github").first()

    # Portfolio Logo
    logo_data = MyImage.objects.filter(title="Profile Logo").first()
    leetcode_icon = MyImage.objects.filter(title="Leetcode Icon").first()
    linkedin_icon = MyImage.objects.filter(title="Linkdin").first()
    github_icon = MyImage.objects.filter(title="Github").first()
    hackerrank_icon = MyImage.objects.filter(title="Hackerrank").first()
    context = {
        "Image":{
            "Profile_Logo":logo_data,
            "Leetcode_Icon":leetcode_icon,
            "Linkedin_Icon":linkedin_icon,
            "Github_Icon":github_icon,
            "Hackerrank_Icon":hackerrank_icon
        },
        "Footer":{
            "Address":address_data,
            "Mobile_Number":mobile_data,
            "Email":Email_data,
            "about_me":Footer_About_Me_Data,
            "Leetcode":leetcode_link,
            "Hackerrank":hackerrank_link,
            "Linkedin":linkedin_link,
            "Github":github_link
        },
        "Current_year":current_year
    }
    return context
