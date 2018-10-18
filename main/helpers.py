import requests
from django.conf import settings
from main.models import Data
import json


def compile_fitbit(oh_member):
    fb_user = oh_member.fitbituser
    json_out = {}
    headers = {'Authorization': "Bearer %s" % fb_user.get_access_token()}
    hr = requests.get(
        'https://api.fitbit.com/1/user/-/activities/heart/date/today/1d/1sec.json',
        headers=headers)
    json_out['heart_rate'] = hr.json()['activities-heart-intraday']['dataset'][-1]['value']
    activity = requests.get(
        'https://api.fitbit.com/1/user/-/activities/date/today.json',
        headers=headers)
    json_out['steps'] = activity.json()['summary']['steps']
    sleep = requests.get(
        'https://api.fitbit.com/1.2/user/-/sleep/date/today.json',
        headers=headers)
    json_out['hours_slept'] = round(
        sleep.json()['summary']['totalMinutesAsleep']/60, 2)
    data, _ = Data.objects.get_or_create(
                oh_member=oh_member,
                data_type='fitbit')
    data.data = json.dumps(json_out)
    data.save()



def compile_music(oh_member):
    json_out = {}
    for f in oh_member.list_files():
        if f['basename'] == 'spotify-listening-archive.json' and f['source'] == 'direct-sharing-176':
            spotify = requests.get(f['download_url']).json()
            title = spotify[-1]['track']['name']
            artist = spotify[-1]['track']['artists'][0]['name']
            json_out = {'title': title, 'artist': artist}
    data, _ = Data.objects.get_or_create(
                oh_member=oh_member,
                data_type='music')
    data.data = json.dumps(json_out)
    data.save()


def compile_location(oh_member):
    location_key = settings.TZKEY
    json_data = {}
    for f in oh_member.list_files():
        if f['basename'] == 'overland-data.json' and f['source'] == 'direct-sharing-186':
            overland_data = requests.get(f['download_url']).json()
            lon, lat = overland_data[-1]['geometry']['coordinates']
            json_data['battery_level'] = round(overland_data[-1]['properties']['battery_level'],2)
            json_data['battery_state'] = overland_data[-1]['properties']['battery_state']

            weather_url = (
                "https://query.yahooapis.com/v1/public/yql?q="
                "select%20*%20from%20weather.forecast%20where%20u%3D'c'%20"
                "and%20woeid%20in%20(SELECT%20woeid%20FROM%20geo.places%20"
                "WHERE%20text%3D%22({lat}%2C{lon})%22)"
                "&format=json&env=store%3A%2F%2F"
                "datatables.org%2Falltableswithkeys").format(lat=lat, lon=lon)
            weather = requests.get(weather_url).json()
            weather_data = {}
            place = "{}{}, {}".format(
                weather['query']['results']['channel']['location']['city'],
                weather['query']['results']['channel']['location']['region'],
                weather['query']['results']['channel']['location']['country']
            )
            json_data['place'] = place
            condition = weather['query']['results']['channel']['item']['condition']
            weather_data['temperature_outside'] = condition['temp']
            weather_data['condition_text'] = condition['text']
            weather_data['code'] = condition['code']
            json_data['weather'] = weather_data
            tz = requests.get(
                ('http://api.timezonedb.com/v2.1/get-time-zone?'
                    'key={key}&lat={lat}&lng={lon}&'
                    'by=position&format=json').format(
                        lat=lat, lon=lon, key=location_key)).json()
            json_data['tz'] = tz['abbreviation']
            json_data['tz_offset'] = tz['gmtOffset']

    data, _ = Data.objects.get_or_create(
                oh_member=oh_member,
                data_type='location')
    data.data = json.dumps(json_data)
    data.save()
