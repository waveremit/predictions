import os
from flask import Flask, request
app = Flask(__name__)

@app.route('/', methods=['POST'])
def main():
    return '\n'.join('%s: %s' % (k,v)for (k,v) in request.form.items())

if __name__ == '__main__':
     app.debug = True
     port = int(os.environ.get("PORT", 5000))
     app.run(host='0.0.0.0', port=port)
