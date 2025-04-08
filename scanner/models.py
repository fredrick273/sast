from django.db import models

# Create your models here.
class ScanList(models.Model):
    repo_id = models.CharField(max_length=12)
    token = models.TextField()