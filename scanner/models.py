from django.db import models

# Create your models here.
class ScanList(models.Model):
    repo_id = models.CharField(max_length=12)
    token = models.TextField()

class Reports(models.Model):
    repo = models.ForeignKey(ScanList, on_delete=models.CASCADE)
    datetime = models.DateTimeField(auto_now=True)
    commit_id = models.TextField(null=True,blank=True)
    commit_url = models.TextField(null=True, blank=True)
    analysis_done = models.BooleanField(default=False)