# Global Forest Watch API

This document describes the official Global Forest Watch API.


The API supports analyzing and downloading entire datasets or specific regions of datasets. Regions are specified using a polygon id (country name for example) or a GeoJSON polygon. Supported download formats include Shapefile, GeoJSON, SVG, KML, and CSV. The API is accessed over HTTP from `gfw-apis.appspot.com` and all data is sent and received as JSON.


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
