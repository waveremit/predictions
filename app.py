import os
import json
import shlex

from flask import Flask, request, Response
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 'predictionslocal')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

commands = {}
def command(fn):
    commands[fn.__name__] = fn
    return fn

@command
def help():
    return """\
/predict list
/predict create <contract-name> <contract-terms>
/predict <contract-name> <percentage>
/predict resolve <contract-name> <true|false>"""

@app.route('/', methods=['POST'])
def handle_request():
    if request.form['token'] != os.environ['SLACK_TOKEN']:
        raise Exception('invalid token')

    args = shlex.split(request.form['text'])
    response = dict(response_type='ephemeral',
                    text=commands[args[0]](*args[1:]))

    return Response(json.dumps(response),  mimetype='application/json')

if __name__ == '__main__':
     app.debug = True
     port = int(os.environ.get("PORT", 5000))
     app.run(host='0.0.0.0', port=port)
