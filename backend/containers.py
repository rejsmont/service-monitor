from flask import Blueprint
from pylxd import Client
import os
import urllib3
import yaml
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
blueprint = Blueprint('containers', __name__)
api = None


def __init__():
    global api
    config_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../config')
    config_file = os.path.join(config_dir, 'lxd.yml')
    stream = open(config_file, 'r')
    config = yaml.load(stream, Loader=yaml.Loader)
    if not os.path.isabs(config['certificate']):
        config['certificate'] = os.path.join(config_dir, config['certificate'])
    if not os.path.isabs(config['key']):
        config['key'] = os.path.join(config_dir, config['key'])
    api = Client(
        endpoint=config['server'], verify=False,
        cert=(config['certificate'], config['key'])
    )


@blueprint.route('/containers')
def all_containers():
    containers = {}
    for container in api.containers.all():
        if container.location not in containers:
            containers[container.location] = {}
        containers[container.location][container.name] = container.status
    return containers


__init__()
