from django.contrib import admin
from .models import WorkModel,see_my_work
# Register your models here.

# Work table
@admin.register(WorkModel)
class WorkModelAdmin(admin.ModelAdmin):
    list_display = ("id","title","content","Work_Image")

# see my work table
@admin.register(see_my_work)
class WorkModelAdmin(admin.ModelAdmin):
    list_display = ("work","description","github_link","website_link")