from django.urls import path
from . import views

urlpatterns = [
    path("",views.Work,name="Work"),
    path("<int:Myid>/",views.seemywork,name="see_my_work")
]