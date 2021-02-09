from dataclasses import asdict
from haproxy.dataclasses import Proxy
from flask import Blueprint, jsonify
from urllib.parse import urlparse
import csv
import os
import requests
import urllib3
import yaml
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
blueprint = Blueprint('services', __name__)


def _init_config():
    config_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../config')
    config_file = os.path.join(config_dir, 'haproxy.yml')
    stream = open(config_file, 'r')
    return yaml.load(stream, Loader=yaml.Loader)


config = _init_config()


def AnonKV(**kwargs):
    return type("Object", (), kwargs)()


@blueprint.route('/services')
def all_containers():
    frontends = {}
    backends = {}
    workers = {}
    for server in config['servers']:
        host = urlparse(server).hostname
        with requests.get(server + '/;csv;norefresh') as r:
            stream = (line.decode('utf-8') for line in r.iter_lines())
            rows = csv.DictReader(stream)
            for row in rows:
                svname = row['svname']
                pxname = row['# pxname']
                if svname == 'FRONTEND':
                    if pxname not in frontends:
                        frontends[pxname] = []
                    frontends[pxname].append(asdict(Proxy.from_row(host, row)))
                elif svname == 'BACKEND':
                    if pxname not in backends:
                        backends[pxname] = []
                    backends[pxname].append(asdict(Proxy.from_row(host, row)))
                else:
                    if pxname not in workers:
                        workers[pxname] = []
                    workers[pxname].append(asdict(Proxy.from_row(host, row)))

    return jsonify({
        'frontends': frontends,
        'backends': backends,
        'workers': workers
    })
