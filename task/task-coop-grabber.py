import datetime
import json
import logging
import re
from time import sleep
import time

import pymongo
import requests
# noinspection PyPackageRequirements
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s %(levelname)s %(message)s', datefmt='%d-%m-%y %H:%M:%S')
start_time = time.time()
db = pymongo.MongoClient('mongodb://127.0.0.1:27017').get_database('coop')

url = 'http://www.coop.ch/de/services/standorte-und-oeffnungszeiten.getvstlist.json?lat=47.0547336&lng=8.2122653&start=1&end=1000&filterFormat=restaurant&filterAttribute=&gasIndex=0'
response = requests.get(url)
if response.status_code == 200:
    try:
        data = json.loads(response.text)
        timestamp = datetime.datetime.now()

        logging.info("Grap location Data")
        for restaurant in data['vstList']:
            db_objc = {
                '_id': int(restaurant['betriebsNummerId']['id']),
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

            db.get_collection('locations').update_one({'_id': db_objc['_id']}, {'$set': db_objc}, upsert=True)
            db.get_collection('locations_history').update_one({'_id': db_objc['_id']}, {'$set': db_objc}, upsert=True)

        db.get_collection('locations').update_one({'last_updated': {'$ne': timestamp}}, {'$set': {'open': False}})
        db.get_collection('locations').create_index([('open', pymongo.ASCENDING)])
        db.get_collection('locations').create_index([('last_updated', 1)], expireAfterSeconds=1209600)  # two weeks

        db.get_collection('locations').create_index([('coordinates', '2dsphere'), ('open', pymongo.ASCENDING)])
        db.get_collection('locations_history').create_index([('coordinates', '2dsphere'), ('open', pymongo.ASCENDING)])

        db.get_collection('locations').create_index([('name', pymongo.TEXT)], default_language='german')
        db.get_collection('locations_history').create_index([('name', pymongo.TEXT)], default_language='german')
    except:
        logging.error("Failed to write Location to mongodb")
        pass
else:
    logging.warning("Connection Problem on location grapping, status code: " + str(response.status_code))


# db.get_collection('menus_loading').drop()

# noinspection PyShadowingNames
def get_menus_for_data(response: requests.Response, location_id: int):
    dom = BeautifulSoup(response.text, 'html.parser')

    menus = []
    weekdays = []

    try:
        for element in dom.find('select', {'id': 'wochentag'}).find_all('option'):
            if element.text != "Nächste Woche":
                year = datetime.datetime.now().year
                date = datetime.datetime.strptime(element.text.split(' ')[1] + str(year) + " +0000", '%d.%m%Y %z')
                weekdays.append(date.timestamp())
            else:
                logging.debug("ignore \"Nächste Woche\" on weekday menu grapping")
    except:
        logging.warning("can not fetch weekdays for " + str(location_id))
        pass

    for (index, timestamp) in enumerate(weekdays):
        for row in dom.find('div', {'id': 'weekday_' + str(index)}).find_all('div', {'class': 'RES-APP-001_menu-item'}):
            try:
                title = row.find('div', {'class': 'row RES-APP-001_menu-item--title'}).find_all('img')[0].attrs['alt']
                try:
                    vegi = row.find('div', {'class': 'row RES-APP-001_menu-item--title'}).find_all('img')[1].attrs['data-vegi']
                    if vegi == "vegi":
                        vegetarian = True
                    else:
                        vegetarian = False
                except:
                    vegetarian = False
                    pass
                price = row.find('div', {'class': 'RES-APP-001_menu-item--price'}).text.strip()
                ingredients = [ingredient.strip() for ingredient in row.find('div', {'class': 'RES-APP-001_menu-item--ingredients'}).get_text('\n').split('\n')]
                ingredients = list(filter(None, ingredients))

                menus.append({
                    'location_id': location_id,
                    'vegetarian': vegetarian,
                    'menu': ingredients,
                    'price': float(price),
                    'timestamp': weekdays[index],
                    'title': title
                })
            except:
                logging.error("Problem by parsing a menu for " + str(location_id))
                pass

    if len(menus) > 0:
        logging.debug("Add " + str(len(menus)) + " menus from " + str(location_id) + " to collection")
        db.get_collection('menus_loading').insert_many(menus)
    else:
        logging.warning("No menus for " + str(location_id))


def get_menus_for_location(location_id):
    response = requests.get('https://www.coop-restaurant.ch/de/menueseite.vst' + str(location_id) + '.restaurant.html')
    if response.status_code == 200:
        get_menus_for_data(response, location_id)
    else:
        logging.error("Connection Problem on " + str(location_id) + " status code: " + str(response.status_code))


for location in list(db.get_collection('locations').find()):
    logging.info('Fetching ' + location['name'] + " - " + str(location['_id']))

    get_menus_for_location(location['_id'])
    sleep(5)

# old_menus = list(db.get_collection('menus').find({'timestamp': {'$lt': min(all_weekdays)}}))
#
# if len(old_menus) > 0:
#     db.get_collection('menus_history').insert(old_menus)
#
# db.get_collection('menus_history').ensure_index([('location_id', pymongo.ASCENDING)])

logging.info("Create index on collection menus_loading")
db.get_collection('menus_loading').create_index([('location_id', pymongo.ASCENDING), ('timestamp', pymongo.ASCENDING)])

loading_collection_count = db.get_collection('menus_loading').count_documents({})

if "menus" in db.list_collection_names():
    collection_count = db.get_collection('menus').count_documents({})
else:
    logging.info("first init and menus collection doesn't exists")
    collection_count = 0

logging.info("Loading collection has " + str(loading_collection_count) + " menus, the old collection has " + str(collection_count))

logging.info("Switch collection menus_loading to menus")
db.get_collection('menus_loading').rename('menus', dropTarget=True)

end_time = time.time()
hours, rem = divmod(end_time-start_time, 3600)
minutes, seconds = divmod(rem, 60)
logging.info("Finish data grapping from coop until {:0>2}:{:0>2}:{:05.2f}".format(int(hours),int(minutes),seconds))
