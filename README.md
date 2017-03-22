# Predictions

A CFAR-style prediction market for Slack.

## Installation

This code needs to run on a server that Slack can forward commands to, and it
needs to have a Postgres database available.  Within Wave this is deployed on
Heroku.  This is convenient, because Heroku manages both the web server and the
database server for you, but it's also more expensive.  A cheaper option would
be to either install this on a server you're already running, or on a small
VPS, but then you need to do more of the ops work yourself.

## Development Setup

To set up a new local clone for development, do this once:

    git clone git@github.com:waveremit/predictions
    cd predictions
    source virtualenv.sh

Then, `workon predictions` will take you into the proper environment. If there
have been changes to the requirements file, run `pip install -r requirements
.txt`.

## Deployment

Within Wave, PRs are auto-deployed to Heroku after merging to master, if they
pass CI.

If you modified the models, there isn't any automated migration system.  You
have to run the sql commands manually to make the current DB match your model.

## Tests

### Automated tests

    pytest .

### Manual testing:

In one terminal:

    createdb predictionslocal
    SLACK_TOKEN=1 python app.py

In another:

    curl -d 'token=1&user_name=test&text=COMMAND' localhost:5000
