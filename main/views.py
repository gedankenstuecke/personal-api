from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import redirect, render
from django.utils.safestring import mark_safe
from django.http import JsonResponse
import base64
import requests
import json
import arrow
from openhumans.models import OpenHumansMember
from .models import FitbitUser, Data, NetatmoUser, LastFmUser


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
        if hasattr(request.user.openhumansmember, 'lastfmuser'):
            context['lastfmuser'] = request.user.openhumansmember.lastfmuser.username
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
        if hasattr(request.user.openhumansmember, 'netatmouser'):
            context['netatmouser'] = request.user.openhumansmember.netatmouser
        context['netatmo_link'] = "https://api.netatmo.com/oauth2/authorize?client_id={}&redirect_uri={}&scope=read_station&state=random_string".format(
            settings.NETATMO_CLIENT_ID,
            settings.OPENHUMANS_APP_BASE_URL+'/netatmo/authorized'
        )
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


def create_lastfm(request):
    """
    collect fitbit client id/Secret
    """
    if request.method == 'POST':
        if hasattr(request.user.openhumansmember, 'lastfmuser'):
            lastfm_user = request.user.openhumansmember.lastfmuser
        else:
            lastfm_user = LastFmUser()
        lastfm_user.oh_member = request.user.openhumansmember
        lastfm_user.username = request.POST.get('username')
        lastfm_user.save()
    return redirect('/')


def delete_fitbit(request):
    if request.method == 'POST':
        fb = request.user.openhumansmember.fitbituser
        fb.delete()
        return redirect('/')


@csrf_exempt
def deauth_hook(request):
    if request.method == 'POST':
        print(request.body)
        print(request.META)
        print(json.loads(request.body))
        print(request.POST.get('project_member_id'))
        print(request.POST.get('erasure_requested'))
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
    try:
        oura_sleep = Data.objects.get(
            oh_member=oh_member,
            data_type='oura-sleep'
        )
    except:
        oura_sleep = ""
    try:
        netatmo = Data.objects.get(
            oh_member=oh_member,
            data_type='netatmo'
        )
    except:
        netatmo = ""
    try:
        lastfm = Data.objects.get(
            oh_member=oh_member,
            data_type='music_lastfm'
        )
    except:
        lastfm = ""
    json_data = {}
    if fitbit:
        json_data['activity'] = json.loads(fitbit.data)
    if spotify:
        json_data['music'] = json.loads(spotify.data)
    if location:
        json_data['location'] = json.loads(location.data)
    if oura_sleep:
        json_data['oura_sleep'] = json.loads(oura_sleep.data)
    if netatmo:
        json_data['netatmo'] = json.loads(netatmo.data)
    if lastfm:
        json_data['lastfm'] = json.loads(lastfm.data)
    response = JsonResponse(json_data)
    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response["Access-Control-Max-Age"] = "1000"
    response["Access-Control-Allow-Headers"] = "X-Requested-With, Content-Type"
    return response


def deliver_lametric(request, oh_id):
    oh_member = OpenHumansMember.objects.get(oh_id=oh_id)
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
    try:
        netatmo = Data.objects.get(
                        oh_member=oh_member,
                        data_type='netatmo')
    except:
        netatmo = ""
    json_data = {}
    frames = []

    if location:
        loc_json = json.loads(location.data)
        frames.append({"icon": 2351, 'text': "Bastian is in " + loc_json['place']})

    if spotify:
        music_json = json.loads(spotify.data)
        frames.append({"icon": 15912, "text": "Bastian listened to {} by {}".format(music_json['title'], music_json['artist'])})
    if netatmo:
        netatmo_data = json.loads(netatmo.data)
        frames.append({"icon": 4744, "text": "The CO2 level at home is {} ppm".format(netatmo_data['CO2'])})
        frames.append({"icon": 96, "text": "The temperature is {} °C (outdoor) & {} °C (indoor)".format(netatmo_data['outdoor_temperature'], netatmo_data['indoor_temperature'])})

    response = JsonResponse({"frames": frames})
    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response["Access-Control-Max-Age"] = "1000"
    response["Access-Control-Allow-Headers"] = "X-Requested-With, Content-Type"
    return response


def complete_netatmo(request):

    code = request.GET['code']

    payload = {
        'code': code,
        'grant_type': 'authorization_code',
        'client_id': settings.NETATMO_CLIENT_ID,
        'client_secret': settings.NETATMO_CLIENT_SECRET,
        'redirect_uri': settings.OPENHUMANS_APP_BASE_URL+'/netatmo/authorized',
        'scope': "read_station"
        }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded;chartset=UTF-8'
        }
    # Make request for access token
    r = requests.post(
            'https://api.netatmo.com/oauth2/token', payload, headers=headers)

    rjson = r.json()
    print(rjson)
    if hasattr(request.user.openhumansmember, 'netatmouser'):
        netatmo_user = request.user.openhumansmember.netatmouser
    else:
        netatmo_user = NetatmoUser()
    netatmo_user.oh_member = request.user.openhumansmember
    # Save the user as a FitbitMember and store tokens
    netatmo_user.access_token = rjson['access_token']
    netatmo_user.refresh_token = rjson['refresh_token']
    netatmo_user.expires_in = str(arrow.now().shift(seconds=rjson['expires_in']))
    netatmo_user.save()

    return redirect('/')


def delete_netatmo(request):
    if request.method == 'POST':
        na = request.user.openhumansmember.netatmouser
        na.delete()
        return redirect('/')
