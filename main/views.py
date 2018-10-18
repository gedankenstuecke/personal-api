from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.safestring import mark_safe
from django.http import JsonResponse
import base64
import requests
import json
from openhumans.models import OpenHumansMember
from .models import FitbitUser, Data


def index(request):
    """
    Starting page for app.
    """
    try:
        auth_url = OpenHumansMember.get_auth_url()
    except ImproperlyConfigured:
        auth_url = None
    if not auth_url:
        messages.info(request,
                      mark_safe(
                          '<b>You need to set up your ".env"'
                          ' file!</b>'))

    context = {'auth_url': auth_url}
    if request.user.is_authenticated:
        context['fb_redirect_uri'] = (
            settings.OPENHUMANS_APP_BASE_URL+'/'
            'fitbit/authorized')
        if hasattr(request.user.openhumansmember, 'fitbituser'):
            context['fitbituser'] = request.user.openhumansmember.fitbituser
            if not request.user.openhumansmember.fitbituser.access_token:
                fb_user = request.user.openhumansmember.fitbituser
                fb_auth_url = (
                 'https://www.fitbit.com/oauth2/authorize?response_type=code'
                 '&client_id='+fb_user.personal_client_id+'&scope'
                 '=activity%20nutrition%20heartrate%20location'
                 '%20nutrition%20profile%20settings%20sleep%20social%20weight'
                 '&redirect_uri='+settings.OPENHUMANS_APP_BASE_URL+'/'
                 'fitbit/authorized')
                context['fb_auth_url'] = fb_auth_url
    return render(request, 'main/index.html', context=context)


def about(request):
    """
    give FAQ and further details on the app
    """
    return render(request, 'main/about.html')


def logout_user(request):
    """
    Logout user
    """
    if request.method == 'POST':
        logout(request)
    redirect_url = settings.LOGOUT_REDIRECT_URL
    return redirect(redirect_url)


def create_fitbit(request):
    """
    collect fitbit client id/Secret
    """
    if request.method == 'POST':
        if hasattr(request.user.openhumansmember, 'fitbituser'):
            fb_user = request.user.openhumansmember.fitbituser
        else:
            fb_user = FitbitUser()
        fb_user.oh_member = request.user.openhumansmember
        fb_user.personal_client_id = request.POST.get('client_id')
        fb_user.personal_client_secret = request.POST.get('client_secret')
        fb_user.access_token = ''
        fb_user.refresh_token = ''
        fb_user.save()
    return redirect('/')


def delete_fitbit(request):
    if request.method == 'POST':
        fb = request.user.openhumansmember.fitbituser
        fb.delete()
        return redirect('/')


def complete_fitbit(request):

    code = request.GET['code']

    # Create Base64 encoded string of clientid:clientsecret for the headers
    # https://dev.fitbit.com/build/reference/web-api/oauth2/#access-token-request
    fb_user = request.user.openhumansmember.fitbituser
    client_id = fb_user.personal_client_id
    client_secret = fb_user.personal_client_secret
    encode_fitbit_auth = str(client_id) + ":" + str(client_secret)
    print(encode_fitbit_auth)
    b64header = base64.b64encode(
                    encode_fitbit_auth.encode("UTF-8")).decode("UTF-8")
    # Add the payload of code and grant_type. Construct headers
    payload = {
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri':  settings.OPENHUMANS_APP_BASE_URL+'/fitbit/authorized'
        }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': 'Basic %s' % (b64header)}
    # Make request for access token
    r = requests.post(
            'https://api.fitbit.com/oauth2/token', payload, headers=headers)
    # print(r.json())

    rjson = r.json()
    print(rjson)

    # Save the user as a FitbitMember and store tokens
    fb_user.user_id = rjson['user_id']
    fb_user.access_token = rjson['access_token']
    fb_user.refresh_token = rjson['refresh_token']
    fb_user.expires_in = rjson['expires_in']
    fb_user.scope = rjson['scope']
    fb_user.token_type = rjson['token_type']
    fb_user.save()

    return redirect('/')


def deliver_data(request, oh_id):
    oh_member = OpenHumansMember.objects.get(oh_id=oh_id)
    try:
        fitbit = Data.objects.get(
                        oh_member=oh_member,
                        data_type='fitbit')
    except:
        fitbit = ""
    try:
        spotify = Data.objects.get(
                        oh_member=oh_member,
                        data_type='music')
    except:
        spotify = ""
    try:
        location = Data.objects.get(oh_member=oh_member, data_type='location')
    except:
        location = ""
    json_data = {}
    if fitbit:
        json_data['activity'] = json.loads(fitbit.data)
    if spotify:
        json_data['music'] = json.loads(spotify.data)
    if location:
        json_data['location'] = json.loads(location.data)
    response = JsonResponse(json_data)
    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response["Access-Control-Max-Age"] = "1000"
    response["Access-Control-Allow-Headers"] = "X-Requested-With, Content-Type"
    return response
