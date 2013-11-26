# Global Forest Watch API

This document describes the official Global Forest Watch API.

The API supports analyzing and downloading entire datasets or specific regions of datasets. Regions are specified using a polygon id (country name for example) or a GeoJSON polygon. Supported download formats include Shapefile, GeoJSON, SVG, KML, and CSV. The API is accessed over HTTP from `gfw-apis.appspot.com` and all data is sent and received as JSON.

### Analyze and download datasets

Analyze dataset: `GET /datasets/:name` 

http://wip.gfw-apis.appspot.com/datasets/imazon?begin=2009-01-01&end=2013-01-01

Download dataset: `GET /datasets/:name.(svg|geojson|shp|kml|csv)` 

http://wip.gfw-apis.appspot.com/datasets/imazon.svg?begin=2009-01-01&end=2013-01-01

Parameters

Name | Type | Required |Description
--- | --- | --- | ---
begin | string | ✓ | Start date in YYYY-MM-DD format.
end | string | ✓ | Start date in YYYY-MM-DD format.details | string |  | Story details.
iso | string |  | Country ISO code to analyze.
geom | string |  | GeoJSON for area to analyze.


### User submitted stories

The Stories API supports creating, updating, deleting, listing, and searching for stories submitted to Global Forest Watch by members of the community. A story is searchable on content, searchable spatially, and can have multiple media objects associated with it (photos, videos, etc). Users who submit a story are issued a story token used to authenticate future story modifications.

List all stories: `GET /stories`

http://wip.gfw-apis.appspot.com/stories

Get story by id: `GET /stories/:id`

http://wip.gfw-apis.appspot.com/stories/12

```json
{
   "name":"User",
   "title":"Forest saved",
   "media":[
      {
         "url":"http://gfw.stories.s3.amazonaws.com/uploads/big_forest.jpeg",
         "embed_url":"",
         "preview_url":"http://gfw.stories.s3.amazonaws.com/uploads/thumb_forest.jpeg",
         "mime_type":"image/jpeg",
         "order":1
      }
   ],
   "id":12,
   "visible":true,
   "featured":false,
   "geom":{
      "type":"Point",
      "coordinates":[
         23.90625,
         0
      ]
   },
   "details":"Old growth in Congo saved.",
   "date":"2013-11-26T00:00:00+0100",
   "email":"user@gmail.com",
   "location":"Congo, Africa"
}
```

Create new story by POSTing story properties as JSON: `POST /stories/new`
```bash
$ curl -i -d '{"email": "foo", "date": "2013-11-26", "media": [{"url": "foo", "embed_url": "foo", "order": 1, "mime_type": "foo", "preview_url": "foo"}], "geom": {"type": "Point", "coordinates": [23.90625, 0]}, "name": "foo", "title": "foo"}' http://wip.gfw-apis.appspot.com/stories/new
```
Properties

Name | Type | Required |Description
--- | --- | --- | ---
title | string | ✓ | Story title.
details | string |  | Story details.
date | string |  | When the story happened in ISO 8601 format YYYY-MM-DDTHH:MM:SSZ
location | string |  | Where the story happened.
featured | boolean |  | True if the story is featured.
visible | boolean |  | True if the story is visible.
email | string | ✓ | Email of user who submitted story.
name | string | ✓ | Name of user who submitted story.
geom | string | ✓ | GeoJSON object of story location.
token | string |  | User token for authorization.
media | string |  | JSON list of media objects (url, preview_url, embed_url, order, mime_type)

### FORMA alert count by country

`GET /countries/alerts`

http://wip.gfw-apis.appspot.com/countries/alerts

# Developing

The API rides on [Google App Engine](https://developers.google.com/appengine) Python 2.7 runtime, so we just need to [download](https://developers.google.com/appengine/downloads) the latest Python SDK and add it to our PATH. Then checkout the repo:

```bash
$ git clone git@github.com:wri/gfw-api.git
```

And we can run the API using the local development server that ships with App Engine:

```bash
$ cd gfw-api
$ dev_appserver.py .
```

Boom! The webapp is now running locally at [http://localhost:8080](http://localhost:8080) and you get an admin console at [http://localhost:8080/_ah/admin](http://localhost:8080/_ah/admin). Some API methods require a CartoDB API key, so make sure you have a `gfw/cdb.txt` file with the key.

# Deploying

To deploy to App Engine:

```bash
$ cd tools
$ ./deploy.sh {email} {password} {version}
```
