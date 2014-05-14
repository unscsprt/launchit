from django.conf.urls import patterns, include, url
from django.shortcuts import render_to_response, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.views.generic import RedirectView
from rest_framework.renderers import JSONRenderer
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.db import IntegrityError
from models.user_profile import UserProfile
from util.zipcode import zips_view
import json

# Enable the admin site
from django.contrib import admin
admin.autodiscover()

# Import the API
from app import api


class JSONResponse(HttpResponse):
    """
    An HttpResponse that renders it's content into JSON.
    """
    def __init__(self, data, **kwargs):
        content = JSONRenderer().render(data)
        kwargs['content_type'] = 'application/json'
        super(JSONResponse, self).__init__(content, **kwargs)


# define the catch all
def index(request):
    user_json = {}
    if request.user.is_authenticated():
        serialized = api.user.UserSerializer(request.user)
        user_json = serialized.data

    return render_to_response('index.html', {
      'user': request.user,
      'user_json': JSONRenderer().render(user_json)
    })

@csrf_exempt
def register(request):
    data = json.loads(request.body)
    result = {}

    try:
        try:
            User.objects.get(username=data['username'])
            result['result'] = 'error'
            result['message'] = 'That username is taken. Try picking another.'
        except User.DoesNotExist:
            # create user
            user = User()
            user.username = data['username']
            user.email = data['email']
            user.set_password(data['password'])
            user.save()

            # create user profile
            profile = UserProfile(user=user)
            profile.zipcode = data['zipcode']
            profile.save()

            user = authenticate(username=data['username'], password=data['password'])
            if user is not None:
                if user.is_active:
                    login(request, user)
                    request.user = user

                    # Once we have logged the user in return the serialized response
                    serializer = api.user.UserSerializer(request.user)
                    response = JSONResponse(serializer.data)
                    response.status_code = 201
                    return response

    except IntegrityError:
        result['result'] = 'error'
        result['message'] = 'A database error occurred.'

    response = JSONResponse(result)
    response.status_code = 409
    return response

def auth(request):
    data = {}

    if 'HTTP_AUTHORIZATION' in request.META:
        uname, passwd = request.META['HTTP_AUTHORIZATION'].split(':')
        user = authenticate(username=uname, password=passwd)
        if user is not None:
            if user.is_active:
                login(request, user)
                request.user = user

                # Once we have logged the user in return the serialized response
                serializer = api.user.UserSerializer(request.user)
                return JSONResponse(serializer.data)

    data['result']  = "error"
    data['message'] = "Incorrect username or password."

    # They did not provide basic authentication
    response = JSONResponse(data)
    response.status_code = 401
    return response


def vlogout(request):
    logout(request)
    return redirect('/')

urlpatterns = patterns('',
    # Uncomment the next line to enable the admin:
    url(r'^admin/?', include(admin.site.urls)),

    url(r'^api', include(api.urls)),

    url(r'^zips', zips_view),

    # log in, log out routes.
    url(r'^auth/?', auth, name='auth'),
    url(r'^logout/?', vlogout, name='logout'),
    url(r'^register/?', register, name='register'),

    # Catch all, for history API routing
    url(r'^/?$', index, name='index')
)