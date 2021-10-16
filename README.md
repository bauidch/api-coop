# Coop API

This is a fork of [jeremystucki/coop](https://github.com/jeremystucki/coop)
An unofficial Coop Restaurant API

## API
The api is hosted at https://api-coop.svc.bauid.ch


### Locations
`GET /v1/locations`

#### Parameters
latitude and longitude | query | limit | description
--- | --- | --- | ---
-| - | - | Get all locations
X | - | _optional_ | Get all locations, sorted by distance
-| X | _optional_ | Get all locations, sorted by relevance

```json
{
  "results": [
    {
      "id": 2257,
      "name": "Kriens Schappe Bistro",
      "location": {
        "coordinates": [
          <long>,
          <lat>
        ],
        "address": {
          "city": "Kriens",
          "house_number": "2",
          "street": "Hobacherweg",
          "zip": 6010
        }
      }
    }, ...
  ]
}
```

### Location detail
`GET /api/v1/locations/<id>`
```json
{
  "id": 2524,
  "name": "Baden",
  "location": {
    "coordinates": [
      <long>,
      <lat>
    ],
    "address": {
      "city": "Baden",
      "house_number": "28",
      "street": "Bahnhofstrasse",
      "zip": 5401
    }
  }
}
```

### Menus

#### All menus for location
`GET /v1/locations/<id>/menus`

#### All menus for today
`GET /v1/locations/<id>/menus/today`

#### All menus for a specific date
`GET /v1/locations/<id>/menus/<timestamp>` // Midnight GMT

```json
{
  "results": [
    {
      "menu": [
        "Spare-Ribs",
        "BBQ-Sauce",
        "Baked Potatoes",
        "Maiskolben"
      ],
      "price": 13.95,
      "timestamp": 1493078400.0,
      "title": "Wochenmen\u00fc"
    }, ...
  ]
}
```


## Datasource
coop.ch

### Orginal Repo
This is fork of [jeremystucki/coop](https://github.com/jeremystucki/coop)
