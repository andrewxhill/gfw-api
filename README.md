# Global Forest Watch API

This document describes the official Global Forest Watch API.


The API supports analyzing and downloading entire datasets or specific regions of datasets. Regions are specified using a polygon id (country name for example) or a GeoJSON polygon. Supported download formats include Shapefile, GeoJSON, SVG, KML, and CSV. The API is accessed over HTTP from `gfw-apis.appspot.com` and all data is sent and received as JSON. It is hypermedia-enabled which means it supports [URI templates](http://tools.ietf.org/html/rfc6570) for programatically constructing related API endpoints.


## Imazon examples

```
GET /api/datasets/imazon
```

```json
{
   "units":"meters",
   "url":"http://gfw-apis.appspot.com/api/datasets/imazon",
   "download_url":"http://gfw-apis.appspot.com/api/datasets/imazon{.extension}",
   "name":"Imazon",
   "value":24936257111.998199
}
```

To download these results, check out the `download_url` property in the above response object. That's a URI template that can be expanded programatically into a download link for any desired format:

```ruby
# Ruby: https://github.com/hannesg/uri_template
tmpl = URITemplate.new(download_url)
tmpl.expand :extension => "svg"
"http://gfw-apis.appspot.com/api/datasets/imazon.svg"
```

```javascript
// JavaScript: https://github.com/fxa/uritemplate-js
var tmpl = UriTemplate.parse(download_url);
tmpl.expand({extension: 'shp'});
"http://gfw-apis.appspot.com/api/datasets/imazon.shp"
```

Now let's analyze the Imazon dataset withing a GeoJSON polygon using the following URL parameters:

Parameter | Type | Description 
-----|------|--------------
geom | string | GeoJSON polygon

Given a GeoJSON polygon:

```json
{
   "type":"Polygon",
   "coordinates":[
      [
         [
            -56.4697265625,
            -0.7470491450051796
         ],
         [
            -57.3486328125,
            -5.266007882805485
         ],
         [
            -51.240234375,
            -7.318881730366743
         ],
         [
            -53.78906249999999,
            -0.39550467153200675
         ],
         [
            -56.4697265625,
            -0.7470491450051796
         ]
      ]
   ]
}
```

We can analyze Imazon within the polygon and get this:

```json
{
   "units":"meters",
   "url":"http://gfw-apis.appspot.com/api/datasets/imazon",
   "download_url":"http://gfw-apis.appspot.com/api/datasets/imazon/7b5c75cd70282377e94e4ca3a90c20b4{.extension}",
   "name":"Imazon",
   "value":1058591613.291
}
```

Again notice the `download_url` template which can be expanded for download URLs in any desired format.


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

Boom! The webapp is now running locally at [http://localhost:8080](http://localhost:8080) and you get an admin console at [http://localhost:8080/_ah/admin](http://localhost:8080/_ah/admin). For a quick sanity check:

[http://localhost:8080/api/v1/defor/analyze/forma/iso/bra/2005-03-05/2006-08-01](http://localhost:8080/api/v1/defor/analyze/forma/iso/bra/2005-03-05/2006-08-01)

Should return something like:

```json
{
  "value": 415498,
  "units": "alerts",
  "value_display": "415,498"
}
```

# Deploying

To deploy to App Engine:

```bash
$ cd tools
$ ./deploy.sh {email} {password} {version}
```
