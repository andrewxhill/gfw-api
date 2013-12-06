# Global Forest Watch API
# Copyright (C) 2013 World Resource Institute
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

"""This module provides App Engine configurations."""

import json
import os
import sys


def fix_path():
    sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))
    sys.path.append(os.path.join(os.path.dirname(__file__), 'gfw'))


fix_path()


def _load_config(name):
    """Return dev config environment as dictionary."""
    path = os.path.join(os.path.abspath(os.path.dirname(__file__)), name)
    try:
        return json.loads(open(path, "r").read())
    except:
        return {}

IS_DEV = 'Development' in os.environ['SERVER_SOFTWARE']

if IS_DEV:
    APP_BASE_URL = 'http://localhost:8080'
    runtime_config = _load_config('dev.json')
else:
    APP_BASE_URL = 'http://gfw-apis.appspot.com'
    runtime_config = _load_config('prod.json')


runtime_config['APP_BASE_URL'] = APP_BASE_URL
runtime_config['IS_DEV'] = IS_DEV

