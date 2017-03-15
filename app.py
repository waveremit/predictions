import os
import json

from flask import Flask, request
app = Flask(__name__)

@app.route('/', methods=['POST'])
def main():
    if request.form['token'] != os.environ['SLACK_TOKEN']:
        raise Exception('invalid token')
    response = dict(response_type='ephemeral',
                    text=request.form['text'])
    return json.dumps(response)

if __name__ == '__main__':
     app.debug = True
     port = int(os.environ.get("PORT", 5000))
     app.run(host='0.0.0.0', port=port)
