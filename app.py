import os
import math
import json
import pytz
import shlex
import tzlocal
import datetime
import inspect
import parsedatetime
from collections import defaultdict
from flask import Flask, request, Response
from flask.ext.sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 'postgres:///predictionslocal')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

now = datetime.datetime.utcnow

class User(db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    slack_id = db.Column(db.UnicodeText, unique=True, nullable=False)

    def __init__(self, slack_id):
        self.slack_id = slack_id

    def __repr__(self):
        return '<User %s>' % (self.slack_id)

class Contract(db.Model):
    contract_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.UnicodeText, unique=True, nullable=False)
    terms = db.Column(db.UnicodeText, nullable=False)
    user = db.relationship('User')
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'),
                        nullable=False)
    when_closes = db.Column(db.DateTime, nullable=False)
    when_created = db.Column(db.DateTime, nullable=False, default=now)
    resolution = db.Column(db.Boolean, nullable=True)
    when_resolved = db.Column(db.DateTime, nullable=True)
    when_cancelled = db.Column(db.DateTime, nullable=True)

    def __init__(self, name, terms, user_id, when_closes):
        self.name = name
        self.terms = terms
        self.user_id = user_id
        self.when_closes = when_closes

    def __repr__(self):
        return '<Contract %s>' % self.name

class Prediction(db.Model):
    prediction_id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Float, nullable=False)
    user = db.relationship('User')
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    contract = db.relationship('Contract')
    contract_id = db.Column(
        db.Integer, db.ForeignKey('contract.contract_id'), nullable=False)
    when_created = db.Column(db.DateTime, nullable=False, default=now)

    def __init__(self, value, user_id, contract_id):
        self.value = value
        self.user_id = user_id
        self.contract_id = contract_id

commands = {}
def command(fn):
    commands[fn.__name__] = fn
    return fn

@command
def help(session, user_name):
    return """\
/predict list
/predict show <contract-name>
/predict create <contract-name> <contract-terms> <when-closes> <house-odds>
/predict <contract-name> <percentage>
/predict resolve <contract-name> <true|false>
/predict more_help"""

@command
def more_help(session, user_name):
    return """\
/predict cancel <contract-name>
/predict list_resolved
/predict list_cancelled"""

class PredictionsError(Exception):
    pass

def dt_to_string(dt):
    dt_now = now()
    delta = abs(dt_now - dt)

    if delta.days:
        s = '%sd' % int(delta.days)
    elif delta.seconds > 60*60:
        s = '%shr' % int(delta.seconds/60/60)
    elif delta.seconds > 60:
        s = '%smin' % int(delta.seconds/60)
    else:
        s = '%ss' % int(delta.seconds)

    if dt_now > dt:
        return '%s ago' % s
    else:
        return '%s from now' % s

def get_contract_or_raise(session, contract_name):
    contract = session.query(Contract).filter(
        Contract.name == contract_name).one_or_none()
    if not contract:
         raise PredictionsError('unknown contract %s' % contract_name)
    return contract

@command
def list(session, user):
    r = []
    for contract in session.query(Contract).filter(
            Contract.resolution == None,
            Contract.when_cancelled == None):
        r.append(contract.name)
    if not r:
        return 'no active contracts'
    return '\n'.join(r)

@command
def list_cancelled(session, user):
    r = []
    for contract in session.query(Contract).filter(
            Contract.when_cancelled != None):
        r.append(contract.name)
    if not r:
        return 'no cancelled contracts'
    return '\n'.join(r)

@command
def list_resolved(session, user):
    r = []
    for contract in session.query(Contract).filter(
            Contract.resolution != None,
            Contract.when_cancelled == None):
        r.append(contract.name)
    if not r:
        return 'no resolved contracts'
    return '\n'.join(r)

@command
def show(session, user, contract_name):
    contract = get_contract_or_raise(session, contract_name)

    if contract.when_cancelled != None:
        resolution = 'Cancelled'
    elif contract.resolution is None:
        resolution = 'Unresolved'
    else:
        resolution = 'Resolved %s' % (contract.resolution)

    predictions = []
    previous = None
    seen_non_house = False
    scores = defaultdict(float)
    for prediction in session.query(Prediction).filter(
        Prediction.contract_id == contract.contract_id).order_by(
            Prediction.when_created):
        predictions.append('%.2f%%   %s (%s)' % (
            prediction.value*100, prediction.user.slack_id,
            dt_to_string(prediction.when_created)))

        if (contract.when_cancelled == None and
            contract.resolution is not None):
            if prediction.user_id != contract.user_id:
                # You don't get points for creating a contract and then betting
                # on it yourself before anyone else does.  Just treat those as
                # house odds.
                seen_non_house = True

            if previous and seen_non_house:
                if contract.resolution:
                    ratio = prediction.value / previous.value
                else:
                    ratio = (1-prediction.value) / (1-previous.value)
                points = 100*math.log(ratio)
                scores[prediction.user.slack_id] += points
            previous = prediction

    dt_now = now()
    if contract.when_closes < dt_now:
        if contract.when_cancelled != None:
            close_info = ''
        else:
            close_info = 'Closed %s\n' % dt_to_string(contract.when_closes)
    else:
        if contract.resolution != None or contract.when_cancelled != None:
            close_info = 'Was to close %s\n' % dt_to_string(
                contract.when_closes)
        else:
            close_info = 'Closes %s (%s UTC)\n' % (
                dt_to_string(contract.when_closes), contract.when_closes)

    scoring = ''
    if scores:
        scoring = '\n\nscores:\n-------\n' + '\n'.join('%s: %.2f' % (
            slack_id, points) for (points, slack_id) in sorted(
                [(v,k) for (k,v) in scores.items()], reverse=True))

    return '%s (%s)\n%s\n%s%s' % (
        contract.terms, resolution, close_info, '\n'.join(predictions),
        scoring)

@command
def create(session, user, contract_name, terms, when_closes, house_odds):
    if session.query(Contract).filter(
            Contract.name == contract_name).one_or_none():
        raise PredictionsError('A contract named %s already exists' %
                               contract_name)

    try:
        when_closes, _ = parsedatetime.Calendar().parseDT(
            when_closes, tzinfo=tzlocal.get_localzone())
    except ValueError:
        raise PredictionsError('Couldn\'t interpret "%s" as a datetime' %
                               when_closes)
    when_closes = when_closes.astimezone(pytz.utc).replace(tzinfo=None)
    session.add(Contract(name=contract_name, terms=terms,
                         user_id=user.user_id, when_closes=when_closes))
    # set the house odds
    predict(session, user, contract_name, house_odds)
    return 'Created contract %s open until %s' % (
        contract_name, dt_to_string(when_closes))

@command
def predict(session, user, contract_name, percentage):
    contract = get_contract_or_raise(session, contract_name)

    if contract.resolution != None:
        raise PredictionsError('contract %s is already resolved' %
                               contract_name)

    if contract.when_cancelled != None:
        raise PredictionsError('contract %s was cancelled' %
                               contract_name)

    if contract.when_closes < now():
        raise PredictionsError('contract %s closed at %s' %
                               (contract_name, contract.when_closes))

    try:
        if '%' in percentage:
            value = float(percentage.replace('%', '')) / 100
        else:
            value = float(percentage)
    except ValueError:
        raise PredictionsError('%s is not a valid float' % percentage)

    if value >= 1:
         raise PredictionsError('percentage >= 100%%: %s' % percentage)
    elif value <= 0:
         raise PredictionsError('percentage <= 0%%: %s' % percentage)

    session.add(Prediction(value=value, user_id=user.user_id,
                           contract_id=contract.contract_id))
    return 'Added prediction for %s at %s%%' % (contract_name, value*100)

@command
def resolve(session, user, contract_name, resolution):
    contract = get_contract_or_raise(session, contract_name)

    if contract.resolution != None:
        raise PredictionsError('contract %s is already resolved' %
                               contract_name)

    if contract.user_id != user.user_id:
         raise PredictionsError('Only %s can resolve %s' % (
             contract.user.slack_id, contract_name))

    if resolution.lower() not in ['true', 'false']:
         raise PredictionsError(
             'Predictions must be resolved to "true" or "false"; '
             'got "%s"' % resolution)

    contract.resolution = (resolution.lower() == 'true')
    contract.when_resolved = now()
    return 'Contract %s resolved as %s' % (contract_name, contract.resolution)

@command
def cancel(session, user, contract_name):
    contract = get_contract_or_raise(session, contract_name)

    if contract.when_cancelled != None:
        raise PredictionsError('contract %s was already cancelled' %
                               contract_name)

    if contract.user_id != user.user_id:
         raise PredictionsError('Only %s can cancel %s' % (
             contract.user.slack_id, contract_name))

    contract.when_cancelled = now()
    return 'Contract %s cancelled' % contract_name

def lookup_or_create_user(session, slack_id):
    user = session.query(User).filter(
        User.slack_id == slack_id).one_or_none()
    if user:
        return user

    user = User(slack_id=slack_id)
    session.add(user)
    return user

@app.route('/', methods=['POST'])
def handle_request():
    if request.form['token'] != os.environ['SLACK_TOKEN']:
        raise Exception('invalid token')

    args = shlex.split(request.form['text'])
    try:
        session = db.session
        user = lookup_or_create_user(session, request.form['user_name'])
        internal_args = [session, user]
        command_str = 'predict'
        if args[0] in commands:
            command_str = args[0]
            args = args[1:]
        selected_command = commands[command_str]

        expected_args = [x for x in inspect.signature(
            selected_command).parameters][len(internal_args):]

        if len(args) != len(expected_args):
            raise PredictionsError('usage is %s %s' % (
                command_str, ' '.join(
                    '<%s>' % arg for arg in expected_args)))

        response = selected_command(*internal_args, *args)
        session.commit()
    except Exception as e:
        session.rollback()
        if isinstance(e, PredictionsError):
            return 'Error: %s' % str(e)
        else:
            raise
    finally:
        session.close()

    return Response(json.dumps(
        dict(response_type='in_channel', text=response)),
                    mimetype='application/json')

if __name__ == '__main__':
     app.debug = True
     db.create_all()
     port = int(os.environ.get("PORT", 5000))
     app.run(host='0.0.0.0', port=port)
