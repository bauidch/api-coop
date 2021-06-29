import datetime
import json
import re
from time import sleep

import pymongo
import requests
# noinspection PyPackageRequirements
from bs4 import BeautifulSoup

url = 'http://www.coop.ch/de/services/standorte-und-oeffnungszeiten.getvstlist.json?lat=47.0547336&lng=8.2122653&start=1&end=1000&filterFormat=restaurant&filterAttribute=&gasIndex=0'
db = pymongo.MongoClient().get_database('coop')

response = requests.get(url)
data = json.loads(response.text)

timestamp = datetime.datetime.now()

for restaurant in data['vstList']:
    db_objc = {
        '_id': restaurant['betriebsNummerId']['id'],
        'coordinates': {
            'type': 'Point',
            'coordinates': [restaurant['geoKoordinaten']['longitude'], restaurant['geoKoordinaten']['latitude']]
        },
        'address': {
            'street': restaurant['strasse'],
            'house_number': restaurant['hausnummer'],
            'city': restaurant['ort'],
            'postcode': int(restaurant['plz'])
        },
        'name': restaurant['name'],
        'last_updated': timestamp
    }

    db.get_collection('locations').update({'_id': db_objc['_id']}, {'$set': db_objc}, upsert=True)
    db.get_collection('locations_history').update({'_id': db_objc['_id']}, {'$set': db_objc}, upsert=True)

db.get_collection('locations').update({'last_updated': {'$ne': timestamp}}, {'$set': {'open': False}})
db.get_collection('locations').ensure_index([('open', pymongo.ASCENDING)])
db.get_collection('locations').ensure_index([('last_updated', 1)], expireAfterSeconds=1209600)  # two weeks

db.get_collection('locations').ensure_index([('coordinates', '2dsphere'), ('open', pymongo.ASCENDING)])
db.get_collection('locations_history').ensure_index([('coordinates', '2dsphere'), ('open', pymongo.ASCENDING)])

db.get_collection('locations').ensure_index([('name', pymongo.TEXT)], default_language='german')
db.get_collection('locations_history').ensure_index([('name', pymongo.TEXT)], default_language='german')

# db.get_collection('menus_loading').drop()

all_weekdays = []


# noinspection PyShadowingNames
def get_menus_for_data(response: requests.Response, location_id: int, next_week: bool):
    global all_weekdays

    dom = BeautifulSoup(response.text, 'html.parser')

    menus = []
    weekdays = []

    for element in dom.find('select', {'id': 'wochentag'}).find_all('option'):
        year = datetime.datetime.now().year
        date = datetime.datetime.strptime(element.text.split(' ')[1] + str(year) + " +0000", '%d.%m%Y %z')
        weekdays.append(date.timestamp())

    all_weekdays += weekdays

    for (index, timestamp) in enumerate(weekdays):
        for row in dom.find('div', {'id': 'weekday_' + str(index)}).find_all('div', {'class': 'RES-APP-001_menu-item'}):
            try:
                title = row.find('div', {'class': 'row RES-APP-001_menu-item--title'}).find_all('img')[0].attrs['alt']
                price = row.find('div', {'class': 'RES-APP-001_menu-item--price'}).text.strip()
                ingredients = [ingredient.strip() for ingredient in row.find('div', {'class': 'RES-APP-001_menu-item--ingredients'}).get_text('\n').split('\n')]
                ingredients = list(filter(None, ingredients))

                menus.append({
                    'location_id': int(location_id),
                    'menu': ingredients,
                    'price': float(price),
                    'timestamp': weekdays[index],
                    'title': title
                })
            except:
                pass

    if len(menus) > 0:
        db.get_collection('menus_loading').insert(menus)


def get_menus_for_location(location_id):
    response = requests.get('https://www.coop-restaurant.ch/de/menueseite.vst' + location_id + '.restaurant.html')
    if response.status_code == 200:
        try:
            get_menus_for_data(response, location_id, next_week=False)
        except:
            pass

for location in list(db.get_collection('locations').find()):
    print('Fetching ' + location['name'])

    get_menus_for_location(location['_id'])
    sleep(5)

# old_menus = list(db.get_collection('menus').find({'timestamp': {'$lt': min(all_weekdays)}}))
#
# if len(old_menus) > 0:
#     db.get_collection('menus_history').insert(old_menus)
#
# db.get_collection('menus_history').ensure_index([('location_id', pymongo.ASCENDING)])

db.get_collection('menus_loading').create_index([('location_id', pymongo.ASCENDING), ('timestamp', pymongo.ASCENDING)])
db.get_collection('menus_loading').rename('menus', dropTarget=True)
