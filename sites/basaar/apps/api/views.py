import urllib2
import uuid as libuuid
from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.models import User, Group
from django.db.models import Count
from rest_framework import viewsets
from apps.api.serializers import UserSerializer, GroupSerializer, APINodeSerializer, ProductSerializer
from django.db import IntegrityError
from rest_framework.views import APIView
from rest_framework import authentication, permissions
from rest_framework.response import Response
#from apps.catalogue import models as catalogueModels
from oscar.core.loading import get_class, get_model
from apps.api import models
from datetime import datetime
import json
from django.template.defaultfilters import slugify
from rest_framework import authentication, permissions
from rest_framework.authentication import OAuth2Authentication, BasicAuthentication, SessionAuthentication
from apps.api.permissions import IsOwner

from django.http import Http404


Product = get_model('catalogue', 'Product')
Language = get_model('catalogue', 'Language')
Tag = get_model('catalogue', 'Tags')
Category = get_model('catalogue', 'Category')
ProductClass = get_model('catalogue', 'ProductClass')
Partner = get_model('partner', 'Partner')
StockRecord = get_model('partner', 'StockRecord')

class AuthException(Exception):
    def __init__(self):
        pass
    def __str__(self):
        return repr("Authorization error")

class RootException(Exception):
    def __init__(self):
        pass
    def __str__(self):
        return repr("Cannot create Root-nodes")

# Create your views here.
# API-views
class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer


# this view is used to handle all CMS interaction through collections
# and resources
class CMSView(APIView):
    """
    Returns a list of all items and collections in the provided collection in url if url
    points to a valid collection or item. In case of collections a json list of items and collections
    is returned while in case of a materialitem a json representation of the material is returned.
    """
    #authentication_classes = (OAuth2Authentication, BasicAuthentication, SessionAuthentication)
    #permission_classes = ( IsOwner, ) #permissions.IsAuthenticatedOrReadOnly,
    authentication_classes = (OAuth2Authentication, BasicAuthentication, SessionAuthentication)
    permission_classes = (permissions.IsAuthenticatedOrReadOnly, IsOwner)


    def splitUrl(self, url):
        splitpath = url.lower().split('/')
        splitpath = splitpath[0:]
        splitpath = filter(None,splitpath)

        for x in range(0, len(splitpath)):
            splitpath[x] = slugify(splitpath[x])    #remove bad characters from url
        return splitpath

    def slugifyWholeUrl(self, url):
        urlarray = self.splitUrl(url)
        url= urlarray[0]
        for i in range(1, len(urlarray)):
            url += "/" + urlarray[i]

        return url

    #check whether there is empty strings in the url
    def isValidUrl(self,path):
        splitpath = self.trimTheUrl(path)
        print splitpath
        if len(splitpath) == 0:
            return False
        return True

    #trim unnecessary part of url
    def trimTheUrl(self,path):
        url = path
        url = url[len("/api/cms/"):] #slice the useless part away
        #slice the trailing:
        url = url.strip("/")

        return  url

    def checkIfAlreadyInDb(self, path):
        return models.APINode.objects.filter(uniquePath=self.slugifyWholeUrl(path)).exists()

    #make sure there isn't items in the middle of the given path
    def checkIfItemsInPostPath(self, path):
        urlTokens = self.splitUrl(path)
        pathSoFar = "" #urlTokens[0]
        for i in range(0, len(urlTokens)):
            print pathSoFar
            pathSoFar = pathSoFar.strip("/")
            if models.APINode.objects.filter(uniquePath=pathSoFar, objectType="item").exists():
                #we found an object which is an item and in middle of the given path.
                #because items can't have children, this is an ERROR condition.
                return True
            else:
                pathSoFar += "/" + urlTokens[i]

        print "Lopuksi: " + pathSoFar
        return False


    #after we have verified that the url can be used to create new item or collection, check
    #the path and list not existing collections to be created.
    #If collection exists already, nothing happens.
    def createCollections(self, path, request):
        urlTokens = self.splitUrl(path)
        parentPathSoFar = ""
        pathSoFar = urlTokens[0]
        createdCollection = []

        #check if the first collection exists. If not, throw exception:
        if models.APINode.objects.filter(uniquePath=pathSoFar, objectType="collection").exists() == False:
            raise RootException()



        for i in range(1, len(urlTokens)+1):

            try:
                node = models.APINode.objects.get(uniquePath=pathSoFar, objectType="collection")
                #if models.APINode.objects.filter(uniquePath=pathSoFar, objectType="collection").exists():

                perm = IsOwner()
                if not perm.has_object_permission(request, self, node):
                    raise AuthException()

                #the collection exists, therefore it doesn't need to be created.
                parentPathSoFar = pathSoFar
                if i < len(urlTokens):
                    pathSoFar += "/" + urlTokens[i] #move to the next



            except models.APINode.DoesNotExist:
                #the collection doesn't exist yet so create it:
                newColl = models.APINode.create(pathSoFar, parentPathSoFar, "collection")
                newColl.owner = request.user
                newColl.save()
                parentPathSoFar = pathSoFar
                createdCollection.append(pathSoFar)

                if i < len(urlTokens):
                    pathSoFar += "/" + urlTokens[i] #move to the next

        return "Created collections: " + str(createdCollection)

    #check whether json has items or not
    def checkJsonData(self,request):
        theList = request.DATA
        if len(theList) == 0:
            return False
        try:
            theItems = request.DATA["items"]
        except:
            return  False
        return True

    def postMaterialItem(self, path, request):
        theList = request.DATA["items"]
        createdItems = []


        #TODO: WRITE A PROPER SERIALIZER FOR THIS!!!!!!!!!!!!!!!!!
        for x in theList:
            #create new item
            """item = models.MaterialItem.create()
            item.mTitle = x["title"]
            item.description = x["description"]
            item.materialUrl = x["materialUrl"]
            item.materialType = x["materialType"]
            item.iconUrl = x["iconUrl"]
            item.moreInfoUrl = x["moreInfoUrl"]
            item.bazaarUrl = x["bazaarUrl"]         #TODO: THIS IS PROBLEMATIC
            item.version = x["version"]
            item.status = x["status"]
            item.price = x["price"]
            item.language = x["language"]
            item.issn = x["issn"]
            item.author = User.objects.get(username="admin")    #TODO: User should be set to authenticated user when authentication is done
            """
            #PRODUCT EXPERIMENT


            #Add product into database
            downloads = ProductClass.objects.get(name='downloads')  #TODO: Value should come from material type. Check also existence

            #Create unique UPC
            createdUPC = self.createUPC()

            #TODO: Make a proper serializer
            #TODO: Add oEmbed array thing and TAGS array ja LANGUAGE array
            #TODO: Remove price from model
            #TODO: subject=x["subject"]
            product = Product(title=x["title"], upc=createdUPC, description=x["description"], materialUrl=x["materialUrl"],
                              moreInfoUrl=x["moreInfoUrl"],  uuid=x["uuid"], version=x["version"],
                              maxAge=x["maximumAge"], minAge=x["minimumAge"], contentLicense=x["contentLicense"],
                              dataLicense=x["dataLicense"], copyrightNotice=x["copyrightNotice"], attributionText=x["attributionText"],
                              attributionURL=x["attributionURL"], product_class=downloads)    #TODO: product_class on product type

            #Add fullfilment into database
            author = Partner.objects.get(name=self.splitUrl(path)[0])

            try:
                product.contributionDate = datetime.strptime(x["contributionDate"], "%Y-%m-%d")
            except ValueError:
                return "Items created: " + createdItems + " ERROR: ContributionDate field was in wrong format. Should be yyyy-mm-dd"


            if self.checkIfAlreadyInDb(path + "/" + slugify(product.uuid)):
                return "ERROR: Can't post because an object already exists in this URL. Items created: " + unicode(createdItems)

            createdItems.append(product.title)

            #Download icon
            if x["iconUrl"] is not None:
                self.downloadIcon(x["iconUrl"], createdUPC)

            product.save()
            #create language, Tags and EmbeddedMedia models
            langList = x["language"]
            for lan in langList:
                print lan["lang"]
                #check if the language is already in db, if not create it
                if Language.objects.filter(name=lan["lang"]).exists():
                    l = Language.objects.get(name=lan["lang"])
                    l.hasLanguage.add(product)
                else:
                    langEntry = Language.create()
                    langEntry.name = lan["lang"]
                    langEntry.save()
                    langEntry.hasLanguage.add(product)

            #tags creation
            tagList = x["tags"]
            for tag in tagList:
                print tag["tag"]
                #check if the tag is already in db, if not create it
                if Tag.objects.filter(name=tag["tag"]).exists():
                    t = Tag.objects.get(name=tag["tag"])
                    t.hasTag.add(product)
                else:
                    tagEntry = Tag.create()
                    tagEntry.name = tag["tag"]
                    tagEntry.save()
                    tagEntry.hasTags.add(product)



            f = StockRecord(product=product, partner=author, price_excl_tax=x["price"], price_retail=x["price"], partner_sku=x["uuid"])
            f.save()

            #add APINode for this materialItem
            finalUrl = path + "/" + slugify(product.uuid)
            newColl = models.APINode.create(finalUrl, path, "item")
            newColl.materialItem = product
            newColl.owner = request.user
            newColl.save()


        return "Items created: " + unicode(createdItems)


    def get(self, request):
        isValid = self.isValidUrl(request.path)
        if not isValid:
            return Response("Error: The url is empty.")

        url = self.trimTheUrl(request.path)
        print url

        try:
            target = models.APINode.objects.get(uniquePath=url)
            perm = IsOwner()
            perm.has_object_permission(request, self, target)
            #check is the APINode collection or item:
            if target.objectType == "item":
                #return JSON data of the materialItem:
                serializer = ProductSerializer(target.materialItem)
                return Response(serializer.data)
            else:
                #find objects in this collection
                children = models.APINode.objects.filter(parentPath=target.uniquePath)
                serializer = APINodeSerializer(children, many=True)
                return Response(serializer.data)

        except models.APINode.DoesNotExist:
            return Response("404: No such collection or materialItem.")



    def post(self,request):
        isValid = self.isValidUrl(request.path)
        if not isValid:
            return Response("Error: The url is empty 262.")

        if not self.checkJsonData(request):
            return Response("No JSON data available")

        url = self.trimTheUrl(request.path)
        print url

        #check if the object exists in the db already:
        url = self.slugifyWholeUrl(url)


        if self.checkIfItemsInPostPath(url):
            return Response("ERROR: There is an item in middle of the path. Item's can't have children.")

        #create collections if needed
        try:
            try:
                createdCollections = self.createCollections(url, request)
            except RootException:
                return Response("ERROR: Can't create new root nodes.")
        except AuthException:
            return Response("ERROR: You are not the owner of a node in path.")

        #try to create a new item:
        try:
            createdItems = self.postMaterialItem(url, request)
        except IntegrityError:
            return Response("ERROR: There is already a resource with same uuid. uuid must be unique.")

        return Response(createdCollections + " --- " + createdItems)


    def put(self,request):
        inValidItemsNames = ""
        isValid = self.isValidUrl(request.path)
        if not isValid:
            return Response("Error: The url is empty.")
        url = self.trimTheUrl(request.path)
        print url

        if not self.checkJsonData(request):
            return Response("No JSON data available")

        theList = request.DATA["items"]
        inValidItems = []
        for eachItem in theList:
            finalUrl = url + "/" + slugify(eachItem["title"])
            if not models.APINode.objects.filter(uniquePath=finalUrl).exists():
                inValidItems.append(eachItem["title"])
            else:
                self.updateExistingItem(finalUrl,eachItem)
        if len(inValidItems) == 0:
            return Response("Successfully deleted data")
        else:
            for eachItem in inValidItems:
                inValidItemsNames += eachItem
                inValidItemsNames += ",  "
            return Response("items not found:"+inValidItemsNames)

    def updateExistingItem(self,finalUrl,x):
            """
            itemNode = models.APINode.objects.get(uniquePath=finalUrl)
            item = itemNode.materialItem
            #item = models.MaterialItem.objects.get(id = itemNode.materialItem)
            item.description = x["description"]
            item.materialUrl = x["materialUrl"]
            item.materialType = x["materialType"]
            item.iconUrl = x["iconUrl"]
            item.moreInfoUrl = x["moreInfoUrl"]
            item.bazaarUrl = x["bazaarUrl"]         #TODO: THIS IS PROBLEMATIC
            item.version = x["version"]
            item.status = x["status"]
            item.price = x["price"]
            item.language = x["language"]
            item.issn = x["issn"]
            item.author = User.objects.get(username="admin")    #TODO: User should be set to authenticated user when authentication is done
            item.save()
            """
            #PRODUCT EXPERIMENT
            #TODO::Update the product table of oscar after modifying the exisiting models
            """
            downloads = ProductClass.objects.get(name='downloads')
            p = Product.objects.get(title=x["title"],product_class=downloads)
            p.description=x["description"]
            p.materialUrl=x["materialUrl"]
            p.moreInfoUrl=x["moreInfoUrl"]
            p.save()

            f = StockRecord.objects.get(product=p)
            f.partner=author
            f.price_excl_tax=x["price"]
            f.price_retail=x["price"]
            f.partner_sku=x["issn"]
            f.save()
            """
            pass

    def delete(self,request):
        inValidItemsNames = ""
        isValid = self.isValidUrl(request.path)
        if not isValid:
            return Response("Error: The url is empty.")
        url = self.trimTheUrl(request.path)
        #print url

        if not self.checkJsonData(request):
            return Response("No JSON data available")

        theList = request.DATA["items"]
        inValidItems = []
        for eachItem in theList:
            finalUrl = url + "/" + slugify(eachItem["title"])
            if not models.APINode.objects.filter(uniquePath=finalUrl).exists():
                inValidItems.append(eachItem["title"])
            else:
                self.deleteExisitingItem(finalUrl,eachItem)

        if len(inValidItems) == 0:
            return Response("Successfully deleted data")
        else:
            for eachItem in inValidItems:
                inValidItemsNames += eachItem
                inValidItemsNames += ",  "
            return Response("items not found:"+inValidItemsNames)

    def deleteExisitingItem(self,finalUrl,x):
        itemNode = models.APINode.objects.get(uniquePath=finalUrl)
        itemNode.materialItem.delete()
        itemNode.delete()
        #item.delete()
        #itemNode.delete()

    #Download icon into static folder
    def downloadIcon(self, url, iconName):
        #TODO Image resizing
        allowedMimes = ['image/gif', 'image/jpeg', 'image/png']

        try:
            urlOpener = urllib2.build_opener()

            #Timeout 20s
            page = urlOpener.open(url, None, 20)

            #Get headers
            headers = page.info()

            if headers['content-type'] in allowedMimes:
                image = page.read()
                iconName = iconName + url[-4:]
                #TODO .jpeg?
                filename = 'static/shop/img/icons/' + iconName
                fout = open(filename, "wb")
                fout.write(image)
                fout.close()
            else:
                return False

        except urllib2.URLError, e:
            #TODO better error handling
            if e == 404:
                #TODO return 404 error ?
                return False
            else:
                return False
        except:
                return False


    #Create unique UPC for material
    def createUPC(self):
        UPC = str(libuuid.uuid4())
        UPC = UPC.replace("-", "")
        UPC = UPC[0:10]

        while models.Product.objects.filter(upc=UPC).exists():
            UPC = str(libuuid.uuid4())
            UPC = UPC.replace("-", "")
            UPC = UPC[0:15]

        return UPC
