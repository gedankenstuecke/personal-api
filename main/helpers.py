import requests
from django.conf import settings
from main.models import Data
import json
import pandas
import io
import geopy.distance


def compile_fitbit(oh_member):
    fb_user = oh_member.fitbituser
    json_out = {}
    headers = {'Authorization': "Bearer %s" % fb_user.get_access_token()}
    hr = requests.get(
        'https://api.fitbit.com/1/user/-/activities/heart/date/today/1d/1sec.json',
        headers=headers)
    try:
        json_out['heart_rate'] = hr.json()['activities-heart-intraday']['dataset'][-1]['value']
    except:
        pass
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
    try:
        for f in oh_member.list_files():
            if f['basename'] == 'spotify-listening-archive.json' and f['source'] == 'direct-sharing-176':
                spotify = requests.get(f['download_url']).json()
                title = spotify[-1]['track']['name']
                artist = spotify[-1]['track']['artists'][0]['name']
                json_out = {'title': title, 'artist': artist}
                break
        data, _ = Data.objects.get_or_create(
                    oh_member=oh_member,
                    data_type='music')
        data.data = json.dumps(json_out)
        data.save()
    except:
        pass


def compile_oura_sleep(oh_member):
    json_out = {}
    try:
        for f in oh_member.list_files():
            if f['basename'] == 'oura-data.json' and f['source'] == 'direct-sharing-184':
                oura = requests.get(f['download_url']).json()
                total_duration = oura['sleep'][-1]['duration']
                awake = oura['sleep'][-1]['awake']
                sleep_duration = total_duration - awake
                sleep_duration = round(sleep_duration/60/60, 2)
                oura_steps = oura['activity'][-1]['steps']
                oura_temp = oura['sleep'][-1]['temperature_delta']
                json_out = {
                    'sleep_duration': sleep_duration,
                    'steps': oura_steps,
                    'temperature': oura_temp
                    }
                break
        data, _ = Data.objects.get_or_create(
                    oh_member=oh_member,
                    data_type='oura-sleep')
        data.data = json.dumps(json_out)
        data.save()
    except:
        pass


def compile_location(oh_member):
    location_key = settings.TZKEY
    weather_key = settings.WEATHER_KEY
    json_data = {}
    overland_files = []
    for f in oh_member.list_files():
        if 'processed' in f['metadata']['tags'] and f['source'] == 'direct-sharing-186':
            overland_files.append(f)
    if overland_files:
        latest_overland_file = sorted(overland_files, key=lambda k: k['basename'])[-1]
        ol_handle = requests.get(latest_overland_file['download_url']).content
        try:
            df = pandas.read_csv(io.StringIO(ol_handle.decode('utf-8')))
        except:
            return None

        lon = df.longitude.values[-1]
        lat = df.latitude.values[-1]
        json_data['battery_level'] = round(df.battery_level.values[-1],2)
        json_data['battery_state'] = df.battery_state.values[-1]

        weather_url = 'http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&units=metric&appid={weather_key}'.format(
            lat=lat,
            lon=lon,
            weather_key=weather_key
        )

        weather = requests.get(weather_url).json()
        weather_data = {}
        country_data = requests.get('https://restcountries.eu/rest/v2/alpha/{country_data}'.format(
            country_data=weather['sys']['country']
        )).json()
        place = "{}, {}".format(
            weather['name'],
            country_data['name']
        )
        json_data['place'] = place
        json_data['flag_url'] = country_data['flag']
        weather_data['temperature_outside'] = weather['main']['temp']
        weather_data['condition_text'] = weather['weather'][0]['main']
        weather_data['code'] = weather['weather'][0]['id']
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


def compile_netatmo(oh_member):
    dist = None
    latest_overland_file = None
    overland_files = []
    json_data = {}
    print('get overland in netatmo')
    for f in oh_member.list_files():
        if 'processed' in f['metadata']['tags'] and f['source'] == 'direct-sharing-186':
            overland_files.append(f)
    if overland_files:
        latest_overland_file = sorted(overland_files, key=lambda k: k['basename'])[-1]
        ol_handle = requests.get(latest_overland_file['download_url']).content
        try:
            df = pandas.read_csv(io.StringIO(ol_handle.decode('utf-8')))
        except:
            pass
    print('got overland')
    na = oh_member.netatmouser
    h = {'Authorization': 'Bearer {}'.format(na.get_access_token())}
    resp = requests.get('https://api.netatmo.com/api/getstationsdata?get_favorites=true', headers=h)
    station = resp.json()['body']['devices'][0]
    print('got netatmo')
    if latest_overland_file:
        lon = df.longitude.values[-1]
        lat = df.latitude.values[-1]
        loc = resp.json()['body']['devices'][0]['place']['location']
        dist = round(geopy.distance.distance((lat,lon),(loc[1],loc[0])).km,1)
        json_data['home_distance'] = dist
        print('got distance')
    json_data['CO2'] = station['dashboard_data']['CO2']
    json_data['indoor_temperature'] = station['dashboard_data']['Temperature']
    json_data['pressure'] = station['dashboard_data']['Pressure']
    json_data['noise'] = station['dashboard_data']['Noise']
    outdoor = station['modules'][0]
    json_data['outdoor_temperature'] = outdoor['dashboard_data']['Temperature']
    json_data['outdoor_humidity'] = outdoor['dashboard_data']['Humidity']
    print('create netatmo json')
    data, _ = Data.objects.get_or_create(
                oh_member=oh_member,
                data_type='netatmo')
    data.data = json.dumps(json_data)
    data.save()
    print('saved netatmo json')
