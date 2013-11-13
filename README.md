# What is GFW API?

[Global Forest Watch](http://www.wri.org/our-work/project/global-forest-watch) (GFW) is a powerful, near-real-time forest monitoring system that unites satellite technology, data sharing, and human networks around the world to fight deforestation. This repository contains the GFW API.


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