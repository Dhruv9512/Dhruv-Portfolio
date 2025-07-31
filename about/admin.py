from django.contrib import admin
from .models import Education,Skill,certification_link,Work_Experience_and_Internships
# Register your models here.

# Education
@admin.register(Education)
class EducationModel(admin.ModelAdmin):
    list_display = ("Name","institution","address","status","score")

# Skill
@admin.register(Skill)
class SkillModel(admin.ModelAdmin):
    list_display = ("Name","skill")

# certificates
@admin.register(certification_link)
class certification_linkModel(admin.ModelAdmin):
    list_display = ("name","title","content","link")


# Work Experience & Internships
@admin.register(Work_Experience_and_Internships)
class Work_Experience_and_InternshipsModel(admin.ModelAdmin):
    list_display = ("name","title","content")
