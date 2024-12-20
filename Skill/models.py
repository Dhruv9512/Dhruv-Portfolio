from django.db import models

# Create your models here.

# My projects table
class WorkModel(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=100)
    content = models.CharField(max_length=200)
    Work_Image = models.ImageField(upload_to="Work_Image")

# see my work
class see_my_work(models.Model):
    work = models.ForeignKey('WorkModel', on_delete=models.CASCADE, related_name='see_my_works')
    description = models.TextField() 
    github_link = models.URLField(max_length=300) 
    website_link = models.URLField(max_length=300) 