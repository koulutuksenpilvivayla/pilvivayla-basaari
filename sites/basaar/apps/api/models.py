from django.db import models
from django.contrib.auth.models import User, Group
from oscar.core.loading import get_class, get_model
import datetime
from autoslug import AutoSlugField
# Create your models here.

Product = get_model('catalogue', 'Product')

"""
# fill in all the details we created for the API-definition
# and discuss the rating-thumb thing
class MaterialItem(models.Model):
    mTitle = models.CharField(max_length=256)
    description = models.TextField(max_length=8000)
    materialUrl = models.URLField(max_length=8000)
    materialType = models.CharField(max_length=64)
    iconUrl = models.URLField(max_length=8000)
    screenshotUrls = PickledObjectField()
    videoUrls = PickledObjectField()
    moreInfoUrl = models.URLField(max_length=8000)
    bazaarUrl = models.URLField(max_length=8000)
    version = models.CharField(max_length=256)
    status = models.CharField(max_length=256)
    createdAt =  models.DateTimeField(auto_now_add=True)
    price = models.FloatField(default=0)
    language = models.CharField(max_length=256)
    issn = models.CharField(max_length=256)
    author = models.ForeignKey(User)

    #TODO: TAGS
    #TODO: LICENSE THINGS

    owner_org_name = models.CharField(max_length=255)   #this might be foreignkey
    license = models.CharField(max_length=255)
    free = models.BooleanField(default=True)
    link = models.TextField(max_length=8000)
    itemType = models.CharField(max_length=32)   # trial, full version

    lastModified = models.DateField(auto_now_add=True)
    numberOfRatings = models.IntegerField(default=0)
    numberOfLikes = models.IntegerField(default=0)
    #collectionId= models.ForeignKey(MaterialCollections, default=MaterialCollections.defaultValue)
    author = models.ForeignKey(User)
    uniqueTitle = models.CharField(max_length=8000)
    slug = AutoSlugField(populate_from='mTitle')


    def __str__(self):
        return self.mTitle

    @classmethod
    def create(cls):
        obj = cls()
        return obj
"""


#this is a model which is used to describe the API-structure
class APINode(models.Model):
    uniquePath = models.CharField(max_length=8000)
    parentPath = models.CharField(max_length=8000, blank=True)
    objectType = models.CharField(max_length=20)
    materialItem = models.ForeignKey(Product, blank=True, null=True)
    owner = models.ForeignKey(User)

    def __str__(self):
        return self.uniquePath

    @classmethod
    def create(cls, uniqPath, parPath, objType):
        obj = cls(uniquePath=uniqPath, parentPath=parPath, objectType=objType)
        return obj




