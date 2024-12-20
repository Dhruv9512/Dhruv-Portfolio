from django.db import models

# image class
class MyImage(models.Model):
    title = models.CharField(max_length=100)
    image = models.ImageField(upload_to='MyImages/') 

# Fotter class
class Footer(models.Model):
    title = models.CharField(max_length=100)
    content = models.CharField(max_length=500)

# Resume files
class File(models.Model):
    title = models.CharField(max_length=100)
    content = models.FileField(upload_to='File/')