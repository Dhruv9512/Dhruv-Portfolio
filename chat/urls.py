from django.urls import path
from  . import views


urlpatterns = [
    path("", views.cheat, name="cheat"),
    # path("api/", views.cheatapi, name="cheatapi"),
]

