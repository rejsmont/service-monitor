from flask import Blueprint, jsonify
from pylxd import Client
import os
import urllib3
import yaml
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
blueprint = Blueprint('containers', __name__)


def _init_api():
    global api
    config_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../config')
    config_file = os.path.join(config_dir, 'lxd.yml')
    stream = open(config_file, 'r')
    config = yaml.load(stream, Loader=yaml.Loader)
    if not os.path.isabs(config['certificate']):
        config['certificate'] = os.path.join(config_dir, config['certificate'])
    if not os.path.isabs(config['key']):
        config['key'] = os.path.join(config_dir, config['key'])
    return Client(
        endpoint=config['server'], verify=False,
        cert=(config['certificate'], config['key'])
    )


api = _init_api()


@blueprint.route('/containers')
def all_containers():
    result = {}
    for container in api.containers.all():
        if container.location not in result:
            result[container.location] = {}
        result[container.location][container.name] = str(container.status).lower()
    result = {k: {sk: sv for sk, sv in sorted(v.items(), key=lambda sit: sit[0])}
              for k, v in sorted(result.items(), key=lambda item: item[0])}

    return jsonify({
        'status': 'success',
        'containers': result
    })
