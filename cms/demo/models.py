from django.db import models

class Member(models.Model):
    organisation = models.CharField(max_length=100)
    full_name = models.CharField(max_length=120)
    # email will be added later
