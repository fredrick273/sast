from django.db import models
from django.conf import settings

# Create your models here.
class ScanList(models.Model):
    repo_id = models.CharField(max_length=12)
    token = models.TextField()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True,blank=True)

class Reports(models.Model):
    repo = models.ForeignKey(ScanList, on_delete=models.CASCADE)
    datetime = models.DateTimeField(auto_now=True)
    commit_id = models.TextField(null=True,blank=True)
    commit_url = models.TextField(null=True, blank=True)
    analysis_done = models.BooleanField(default=False)