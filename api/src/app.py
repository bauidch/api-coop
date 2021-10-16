import json
from datetime import datetime
import logging
import sys

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import pymongo
import pytz
from pymongo.errors import ServerSelectionTimeoutError

from .locations import LocationsDAO
from .menus import MenusDAO

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s %(levelname)s %(message)s', datefmt='%d-%m-%y %H:%M:%S')
description = """
api-coop
"""

app = FastAPI(
    title="api-coop",
    description=description,
    version="0.1.1",
    redoc_url=None
    )

logging.info("Start api-coop")

mongo = pymongo.MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=10)
db = mongo.get_database('coop')
locationsDAO = LocationsDAO(db.get_collection('locations'))
menusDAO = MenusDAO(db.get_collection('menus'))


@app.on_event("startup")
async def on_startup():
    try:
        info = mongo.server_info()
    except ServerSelectionTimeoutError:
        logging.error("startup failure, can't connect to mongodb")
        raise


class AddressItem(BaseModel):
    street: str
    house_number: str
    city: str
    postcode: int


class LocationsItem(BaseModel):
    id: int
    name: str
    address: AddressItem


class MenusItem(BaseModel):
    title: str
    menu: str
    price: str
    vegetarian: bool


class ErrorMessage(BaseModel):
    status: str
    message: str


@app.get(
    '/v1/locations/{id}',
    tags=["location"],
    response_model=LocationsItem,
    responses={400: {"model": ErrorMessage}, 404: {"model": ErrorMessage}})
@app.get(
    '/v1/restaurants/{id}',
    description="Get retaurant by id",
    tags=["location"],
    response_model=LocationsItem,
    responses={400: {"model": ErrorMessage}, 404: {"model": ErrorMessage}})
def get_locations_by_id(id: str = None):
    try:
        location_id = int(id)
        location = locationsDAO.get_location(location_id)

        if location is None:
            logging.error("client error: no location with id " + id + " found")
            return JSONResponse(status_code=404, content={"status": "error", "message": "no location found for " + id})

        return JSONResponse(content=location)
    except Exception:
        logging.error("client error: id " + id + " is not an integer")
        return JSONResponse(status_code=400, content={"status": "error", "message": "id must be an integer"})


@app.get('/v1/locations', tags=["location"],  response_model=LocationsItem)
@app.get('/v1/restaurants', tags=["location"],  response_model=LocationsItem)
def get_locations():
    # args = flask.request.args
    # longitude, latitude, query, limit = (None,)*4
    #
    # if 'limit' in args:
    #     try:
    #         limit = int(args['limit'])
    #     except Exception:
    #         return HTTPException(status_code=400, detail="limit must be an integer")
    #
    # if ('latitude' in args) ^ ('longitude' in args):
    #     return HTTPException(status_code=400, detail="must provide latitude and longitude")
    #
    # if 'latitude' in args and 'longitude' in args:
    #     try:
    #         longitude = float(args['longitude'])
    #         latitude = float(args['latitude'])
    #     except Exception:
    #         return HTTPException(status_code=400, detail="latitude and longitude must be numbers")
    #
    # query = args['query'] if 'query' in args else ''
    #
    # if longitude and latitude:
    #     data = locationsDAO.get_locations_with_coordinates(longitude=longitude, latitude=latitude, limit=limit)
    # else:
    data = locationsDAO.get_locations()

    return JSONResponse(content=data)


@app.get('/v1/locations/{id}/menus', tags=["menus"], responses={400: {"model": ErrorMessage}, 500: {"model": ErrorMessage}}, response_model=MenusItem)
@app.get('/v1/locations/{id}/menus/{timestamp}', tags=["menus"], responses={400: {"model": ErrorMessage}, 500: {"model": ErrorMessage}}, response_model=MenusItem)
@app.get('/v1/restaurants/{id}/menus', tags=["menus"], responses={400: {"model": ErrorMessage}, 500: {"model": ErrorMessage}}, response_model=MenusItem)
@app.get('/v1/restaurants/{id}/menus/{timestamp}', tags=["menus"], responses={400: {"model": ErrorMessage}, 500: {"model": ErrorMessage}}, response_model=MenusItem)
def get_menus(id: str, timestamp: str = None):

    try:
        location_id = int(id)
    except Exception:
        return JSONResponse(status_code=400, content={"status": "error", "message": "id must be an integer"})

    if timestamp == 'today':
        date = datetime.now(tz=pytz.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        timestamp = date.timestamp()

    if timestamp is not None:
        try:
            timestamp = int(timestamp)
        except Exception:
            logging.error("client error: 'timestamp " + timestamp + " must be an integer")
            return JSONResponse(status_code=400, content={"status": "error", "message": "timestamp must be an integer"})
    try:
        menus = menusDAO.get_menus(location=location_id, timestamp=timestamp)
        if menus is None:
            JSONResponse(status_code=500, content={"status": "not_found", "message": "no menus found for " + location_id})
        elif menus == "":
            JSONResponse(status_code=500, content={"status": "not_found", "message": "no menus found for " + location_id})
        else:
            return JSONResponse(content=menus)
    except Exception:
        return JSONResponse(status_code=500, content={"status": "error", "message": "failed to get menus"})


@app.get("/health")
def is_database_online():
    try:
        info = mongo.server_info()
        return JSONResponse(status_code=200, content={"database": "UP"})
    except ServerSelectionTimeoutError:
        logging.error("database failure, can't connect to mongodb")
        return JSONResponse(status_code=503, content={"database": "DOWN"})
