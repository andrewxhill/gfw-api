from datetime import date
from dateutil.relativedelta import relativedelta
import itertools
import requests
import urllib
import os


FORMATS = ['shp', 'csv', 'kml', 'geojson', 'svg']

CDB_BASE_URL = 'http://wri-01.cartodb.com/api/v1/sql?'

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
    """Return list of distinct ISO codes."""
    sql = 'SELECT distinct(iso) FROM forma_api ORDER BY iso desc'
    params = urllib.urlencode(dict(q=sql))
    url = '%s%s' % (CDB_BASE_URL, params)
    return map(lambda x: x['iso'], requests.get(url).json()['rows'])


def date_range(begin, end, delta):
    """Generate dates in YYYY-MM-DD format from begin to end via delta."""
    d = begin
    while d <= end:
        yield d.isoformat()
        d += delta


def forma_dates():
    """Return sequence of date tuples for FORMA."""
    begin = date(2006, 1, 1)
    end = date(2014, 2, 1)
    delta = relativedelta(months=+1)
    dates = itertools.product(date_range(begin, end, delta), repeat=2)
    return filter(lambda x: x[0] <= x[1] and x[0] != x[1], dates)


def forma_cache_params():
    """Generate tuples of FORMA cache params (format, iso, begin, end)"""
    for iso in get_iso_codes():
        for begin, end in forma_dates():
            for fmt in FORMATS:
                yield fmt, iso, begin, end


def cache_forma():
    os.chdir('gcs')
    for params in forma_cache_params():
        fmt, iso, begin, end = params
        url = API_ANALYSIS_URL % ('forma', iso, begin, end)
        response = requests.get(url)
        if not response.json()['value']:
            print 'No alerts for %s' % url
        else:
            filename = ANALYSIS_FILENAME % ('forma', begin, end, iso)
            with open(filename, 'wb') as fd:
                for chunk in response.iter_content(chunk_size=10000):
                    fd.write(chunk)
            url = API_DOWNLOAD_URL % ('forma', fmt, iso, begin, end)
            print url
            filename = FILE_NAME % ('forma', begin, end, iso, fmt)
            print filename
            response = requests.get(url)
            with open(filename, 'wb') as fd:
                for chunk in response.iter_content(chunk_size=10000):
                    fd.write(chunk)


def test_forma():
    max_cache = 2
    count = 0
    params = forma_cache_params()
    while count < max_cache:
        fmt, iso, begin, end = params.next()
        url = API_ANALYSIS_URL % ('forma', iso, begin, end)
        analysis = requests.get(url).json()
        if not analysis['value']:
            print 'No alerts for %s' % url
            continue
        url = API_DOWNLOAD_URL % ('forma', fmt, iso, begin, end)
        print url
        filename = FILE_NAME % ('forma', begin, end, iso, fmt)
        print filename
        count += 1
        response = requests.get(url)
        with open(filename, 'wb') as fd:
            for chunk in response.iter_content(chunk_size=10000):
                fd.write(chunk)

if __name__ == '__main__':
    cache_forma()
