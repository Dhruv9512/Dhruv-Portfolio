from distributed import _
from django.db import models

# Create your models here.

# <!-- Education Tab -->
class Education(models.Model):
    Name = models.CharField(max_length=100)
    institution = models.CharField(max_length=255)
    address = models.TextField()
    status = models.CharField(max_length=100)
    score = models.CharField(max_length=100)  

#  <!-- My Skills Tab -->
class Skill(models.Model):
    Name = models.CharField(max_length=150)
    skill = models.CharField(max_length=255)
    Proficiency = models.CharField(max_length=100) 


# <!-- Certifications & Achievements Tab -->
class certification_link(models.Model):
    name = models.CharField(max_length=100)
    title = models.CharField(max_length=150)
    content = models.CharField(max_length=300)
    link = models.CharField(max_length=500)

class Achievements(models.Model):
    name = models.CharField(max_length=150)
    content = models.CharField()


#  <!-- Work Experience / Internships Tab -->
class Work_Experience_and_Internships(models.Model):
    name = models.CharField(max_length=100)
    title = models.CharField(max_length=200)
    content = models.CharField()