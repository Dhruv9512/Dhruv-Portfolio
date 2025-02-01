from django.shortcuts import render
from .models import WorkModel,see_my_work
# Create your views here.

# work page 
def Work(request):

    Work_data = WorkModel.objects.all()

    context = {
        "WorkData":Work_data
    }
    return render(request,"Work/Work.html",context)

# see my work 
def seemywork(request,Myid):
    data = see_my_work.objects.filter(work = int(Myid)).first()

    context = {
        "Data":data,
    }
    return render(request,"see_my_work/see_my_work.html",context)
