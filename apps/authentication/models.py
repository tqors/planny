from django.db import models
from django.contrib.auth.models import AbstractUser

# Base user model
class User(AbstractUser):
    phoneNum = models.CharField(max_length=15, null=True, blank=True)

# Admin subtype
class Admin(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    adminLevel = models.CharField(max_length=50)

# Developer subtype
class Developer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    programmingLanguage = models.CharField(max_length=50)

# Client subtype
class Client(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    companyName = models.CharField(max_length=100)
