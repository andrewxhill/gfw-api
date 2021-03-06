from datetime import date
from dateutil.relativedelta import relativedelta
import itertools
import requests
import urllib
import os
import Queue
import threading
import urllib2
import subprocess
from subprocess import call


FORMATS = ['shp', 'csv', 'kml', 'geojson', 'svg']

CDB_BASE_URL = 'http://wri-01.cartodb.com/api/v2/sql?'

# (dataset, format, iso, begin, end)
API_DOWNLOAD_URL = \
    'http://gfw-apis.appspot.com/datasets/%s.%s?iso=%s&begin=%s&end=%s'

# (dataset, iso, begin, end)
API_ANALYSIS_URL = \
    'http://gfw-apis.appspot.com/datasets/%s?iso=%s&begin=%s&end=%s'

# (dataset, begin, end, iso, format)
FILE_NAME = '%s_%s_%s_%s.%s'

# (dataset, begin, end, iso)
ANALYSIS_FILENAME = '%s_%s_%s_%s.json'


def get_iso_codes():
    """Return list of distinct FORMA ISO codes ordered by country size."""
    # Thanks @d4weed!
    sql = """SELECT DISTINCT(forma_api.iso) as iso,
                             world_countries.area as area
             FROM world_countries
             JOIN forma_api
             ON
             world_countries.iso3 = forma_api.iso
             GROUP BY iso, area
             ORDER BY area DESC"""
    params = urllib.urlencode(dict(q=sql))
    url = '%s%s' % (CDB_BASE_URL, params)
    return map(lambda x: x['iso'], requests.get(url).json()['rows'])


def date_range(begin, end, delta):
    """Generate dates in YYYY-MM-DD format from begin to end via delta."""
    d = begin
    while d <= end:
        yield d.isoformat()
        d += delta


def forma_dates(begin=date(2006, 1, 1), end=date(2014, 2, 1),
    delta=relativedelta(months=+1)):
    """Return sequence of date tuples for FORMA."""
    dates = itertools.product(date_range(begin, end, delta), repeat=2)
    return set(filter(lambda x: x[0] <= x[1] and x[0] != x[1], dates))


def forma_cache_params():
    """Generate tuples of FORMA cache params (format, iso, begin, end)"""
    for iso in get_iso_codes():
        for begin, end in forma_dates():
            for fmt in FORMATS:
                yield fmt, iso, begin, end


#define a worker function
def worker(queue):
    queue_full = True
    while queue_full:
        try:
            params = queue.get(False)
            fmt, iso, begin, end = params
            print 'Processing %s...' % iso
            url = API_ANALYSIS_URL % ('forma', iso, begin, end)
            response = requests.get(url)
            if response.status_code != 200:
                print 'ERROR ANALYSIS: %s (%s)' % (response.text, params)
                continue
            elif not response.json()['value']:
                print 'No alerts for %s' % url
                continue
            else:
                # Analysis result:
                filename = ANALYSIS_FILENAME % ('forma', begin, end, iso)
                with open(filename, 'wb') as fd:
                    for chunk in response.iter_content(chunk_size=10000):
                        fd.write(chunk)
                path = os.path.abspath(filename)
                print subprocess.check_output(['gsutil', 'cp', path,
                                              'gs://gfw-apis-country'])
                # Download result:
                url = API_DOWNLOAD_URL % ('forma', fmt, iso, begin, end)
                filename = FILE_NAME % ('forma', begin, end, iso, fmt)
                response = requests.get(url)
                if response.status_code != 200:
                    print 'ERROR: %s' % response.text
                    continue
                with open(filename, 'wb') as fd:
                    for chunk in response.iter_content(chunk_size=10000):
                        fd.write(chunk)
                path = os.path.abspath(filename)
                print subprocess.check_output(['gsutil', 'cp', path,
                                              'gs://gfw-apis-country'])
        except Queue.Empty:
            queue_full = False
        except Exception, e:
            print 'ERROR: %s' % e
            return


if __name__ == '__main__':
    os.chdir('gcs')

    q = Queue.Queue()
    for params in forma_cache_params():
        q.put(params)

    thread_count = 25
    for i in range(thread_count):
        t = threading.Thread(target=worker, args = (q,))
        t.start()
