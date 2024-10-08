import requests
from django.conf import settings
from main.models import Data
import json
import pandas
import io
import geopy.distance
import numpy as np
import feedparser


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

def higher(value, std_one, std_two):
    if value >= std_two:
        return 2
    elif value >= std_one:
        return 1
    else:
        return 0

def lower(value, std_one, std_two):
    if value <= std_two:
        return 2
    elif value <= std_one:
        return 1
    else:
        return 0


def get_oura_deviations(sleep_data):
    temperature_devs = []
    hr_lowest_devs = []
    breath_average_devs = []
    hrv_devs = []

    for i in sleep_data:
        if i['readiness']:
            if i['readiness']['temperature_deviation']:
                temperature_devs.append(i['readiness']['temperature_deviation'])
        if i['lowest_heart_rate'] != None and i['lowest_heart_rate'] != 255:
            hr_lowest_devs.append(i['lowest_heart_rate'])
        if i['average_breath'] != None and i['average_breath'] != 255:
            breath_average_devs.append(i['average_breath'])
        if i['average_hrv'] != None and i['average_hrv'] != 255:
            hrv_devs.append(i['average_hrv'])

    temp_std_one = np.mean(temperature_devs) + np.std(temperature_devs)
    temp_std_two = np.mean(temperature_devs) + 2*np.std(temperature_devs)
    hr_lowest_std_one = np.mean(hr_lowest_devs) + np.std(hr_lowest_devs)
    hr_lowest_std_two = np.mean(hr_lowest_devs) + 2*np.std(hr_lowest_devs)
    breath_std_one = np.mean(breath_average_devs) - np.std(breath_average_devs)
    breath_std_two = np.mean(breath_average_devs) - 2* np.std(breath_average_devs)
    hrv_std_one = np.mean(hrv_devs) - np.std(hrv_devs)
    hrv_std_two = np.mean(hrv_devs) - 2*np.std(hrv_devs)

    if sleep_data[-1]['readiness']:
        temp = higher(sleep_data[-1]['readiness']['temperature_deviation'],temp_std_one,temp_std_two)
    else:
        temp = 0
    if sleep_data[-1]['lowest_heart_rate']:
        hr = higher(sleep_data[-1]['lowest_heart_rate'], hr_lowest_std_one, hr_lowest_std_two)
    else: 
        hr = 0 
    if sleep_data[-1]['average_breath']:
        breath = lower(sleep_data[-1]['average_breath'],breath_std_one,breath_std_two)
    else:
        breath = 0 
    if sleep_data[-1]['average_hrv']:
        hrv = lower(sleep_data[-1]['average_hrv'], hrv_std_one, hrv_std_two)
    else:
        hrv = 0
    response = {
        'temp': temp, 'hr': hr, 'breath': breath, "hrv": hrv,
        "sum": temp + hr + breath + hrv
    }
    return response


def compile_oura_sleep(oh_member):
    try:
        json_out = {}
        for f in oh_member.list_files():
            if f['basename'] == 'oura-v2-sleep.json' and f['source'] == 'direct-sharing-184':
                oura_sleep = requests.get(f['download_url']).json()
                sleep_duration = round(oura_sleep[-1]['total_sleep_duration']/60/60, 2)
                oura_temp = oura_sleep[-1]['readiness']['temperature_deviation']
                oura_rhr = oura_sleep[-1]['lowest_heart_rate']
                deviations = get_oura_deviations(oura_sleep)
            if f['basename'] == 'oura-v2-daily_activity.json' and f['source'] == 'direct-sharing-184':
                oura_activity = requests.get(f['download_url']).json()
                oura_steps = oura_activity[-1]['steps']
        json_out = {
                    'sleep_duration': sleep_duration,
                    'steps': oura_steps,
                    'temperature': oura_temp,
                    'resting_hr': oura_rhr,
                    'deviations': deviations
                    }
        data, _ = Data.objects.get_or_create(
                    oh_member=oh_member,
                    data_type='oura-sleep')
        data.data = json.dumps(json_out)
        data.save()
    except Exception as error:
        print('oura crashed with ', error)


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
        if json_data['battery_state'] == False:
            json_data['battery_state'] = 'unplugged'
        if json_data['battery_state'] == True:
            json_data['battery_state'] = 'plugged'

        weather_url = 'http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&units=metric&appid={weather_key}'.format(
            lat=lat,
            lon=lon,
            weather_key=weather_key
        )

        weather = requests.get(weather_url).json()
        weather_data = {}
        print(weather)
        country_data = requests.get('https://restcountries.com/v2/alpha/{country_data}'.format(
            country_data=weather['sys']['country']
        )).json()
        print(country_data)
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
        print(json_data)

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
        dist = round(geopy.distance.distance((lat,lon),(loc[1],loc[0])).km, 1)
        json_data['home_distance'] = dist
        print('got distance')
    if 'dashboard_data' in station.keys():
        json_data['CO2'] = station['dashboard_data']['CO2']
        json_data['indoor_temperature'] = station['dashboard_data']['Temperature']
        json_data['pressure'] = station['dashboard_data']['Pressure']
        json_data['noise'] = station['dashboard_data']['Noise']
        outdoor = station['modules'][0]
        json_data['outdoor_temperature'] = outdoor['dashboard_data']['Temperature']
        json_data['outdoor_humidity'] = outdoor['dashboard_data']['Humidity']
    else:
        json_data['CO2'] = 'NA'
        json_data['indoor_temperature'] = 'NA'
        json_data['pressure'] = 'NA'
        json_data['noise'] = 'NA'
        json_data['outdoor_temperature'] = 'NA'
        json_data['outdoor_humidity'] = 'NA'
    print('create netatmo json')
    data, _ = Data.objects.get_or_create(
                oh_member=oh_member,
                data_type='netatmo')
    data.data = json.dumps(json_data)
    data.save()
    print('saved netatmo json')

    s = {station['module_name']: {'temperature': station["dashboard_data"]['Temperature'],
                               'CO2': station["dashboard_data"]['CO2']
                              }}

    for i in station['modules']:
        if 'CO2' in i['dashboard_data']:
            s[i['module_name']] = {
                'temperature': i['dashboard_data']['Temperature'],
                'CO2': i['dashboard_data']['CO2']}
        else:
            s[i['module_name']] = {
                'temperature': i['dashboard_data']['Temperature']}

    data, _ = Data.objects.get_or_create(
                oh_member=oh_member,
                data_type='netatmo_detailed')
    data.data = json.dumps(s)
    data.save()
    print('saved detailed netatmo json')


def compile_lastfm(oh_member):
    json_data = {}
    lfm_user = oh_member.lastfmuser
    request_url = "http://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user={}&api_key={}&format=json&limit=1".format(
    lfm_user.username, settings.LASTFM_KEY
    )
    response = requests.get(request_url).json()
    json_data['artist'] = response['recenttracks']['track'][0]['artist']['#text']
    json_data['song_title'] = response['recenttracks']['track'][0]['name']

    data, _ = Data.objects.get_or_create(
                oh_member=oh_member,
                data_type='music_lastfm')
    data.data = json.dumps(json_data)
    data.save()

def format_bookwyrmhandle(bwh):
    if not bwh.startswith("@"):
        bwh = "@" + bwh
    return bwh


def read_bookwyrm_feed(oh_member):
    bwh = oh_member.bookwyrmhandle.username
    user, server = bwh[1:].split("@")
    feed = "https://{}/user/{}/rss".format(server,user)
    results= feedparser.parse(feed)
    
    for entry in results.entries:
        desc = entry.description
        if desc.startswith("rated <em>"):
            return desc
        elif "finished reading <a href" in desc:
            return desc[desc.find("finished reading <a href"):]
        elif "started reading <a href" in desc:
            return desc[desc.find("started reading <a href"):]
    return ""

def compile_bookwyrm(oh_member):
    json_data = {
        "last_update": read_bookwyrm_feed(oh_member)
    }
    
    data, _ = Data.objects.get_or_create(
                oh_member=oh_member,
                data_type='bookwyrm')
    data.data = json.dumps(json_data)
    data.save()