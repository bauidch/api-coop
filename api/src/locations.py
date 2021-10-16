import pymongo
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s %(levelname)s %(message)s', datefmt='%d-%m-%y %H:%M:%S')


class LocationsDAO:
    def __init__(self, collection: pymongo.collection.Collection):
        self.collection = collection

    # noinspection PyShadowingBuiltins
    def get_location(self, id: int):
        query = {
            '_id': id
        }
        projection = {
            '_id': 1,
            'address': 1,
            'coordinates': 1,
            'name': 1
        }
        location = self.collection.find_one(query, projection)

        if location is not None:
            location['id'] = location.pop('_id')
            return location
        else:
            logging.warning("LocationsDAO  location is none")

    def get_locations(self, search_text: str = '', limit: int = None) -> list:
        query = {}
        projection = {
            '_id': 1,
            'address': 1,
            'coordinates': 1,
            'name': 1
        }

        if search_text != '':
            query['$text'] = {'$search': search_text}

        cursor = self.collection.find(query, projection).sort("name", 1)

        if limit is None:
            data = list(cursor)
        else:
            data = list(cursor.limit(limit))

        for result in data:
            result['id'] = result.pop('_id')

        return data

    def get_locations_with_coordinates(self, longitude: float, latitude: float, limit: int = None) -> list:
        pipeline = [
            {
                '$geoNear': {
                    'near': {
                        'type': 'Point',
                        'coordinates': [longitude, latitude]
                    },
                    'spherical': True,
                    'distanceField': 'distance',
                }
            }, {
                '$project': {
                    '_id': 0,
                    'id': '$_id',
                    'address': 1,
                    'name': 1,
                    'open': 1,
                    'distance': 1,
                    'coordinates': 1
                }
            }
        ]

        if limit is not None:
            pipeline.append({'$limit': limit})

        return list(self.collection.aggregate(pipeline))
