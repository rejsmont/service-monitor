from flask import Flask, jsonify
from flask_cors import CORS
from backend.containers import blueprint as containers
from backend.services import blueprint as services

app = Flask(__name__)
app.register_blueprint(containers)
app.register_blueprint(services)

CORS(app, resources={r'/*': {'origins': '*'}})


# sanity check route
@app.route('/ping', methods=['GET'])
def ping_pong():
    return jsonify('pong!')


if __name__ == '__main__':
    app.run()
