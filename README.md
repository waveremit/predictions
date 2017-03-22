# Predictions

A CFAR-style prediction market for Slack.

## Installation

### Server Setup

This code needs to run on a server that Slack can forward commands to, and it
needs to have a Postgres database available.  Within Wave this is deployed on
Heroku.  This is convenient, because Heroku manages both the web server and the
database server for you, but it's also more expensive.  A cheaper option would
be to either install this on a server you're already running, or on a small
VPS, but then you need to do more of the ops work yourself.

See runtime.txt for the python version this depends on, and requirements.txt
for the dependencies.

### Slack Setup

To make `/predict` work in Slack, you need to tell Slack to forward commands to
your server:

1. Visit https://api.slack.com/apps?new_app=1
2. Enter "Prediction Market" for the name
3. On the next screen, under "Basic Information" / "Building Apps for Slack"
   / "Add features and functionality" choose "Slash Commands"
4. Click "Create New Command"
5. Enter:
   a. Command: "/predict"
   b. Request URL: the url your server is listening on
   c. Short Description: "a prediction market"
   d. Usage Hint: "/predict help"
6. Click "Save"
7. Click "Basic Information" on the left nav under "Settings"
8. Scroll down to "Verification Token" under "App Credentials"
9. Copy that token, and set it as the environment variable `SLACK_TOKEN` on
   your server.  This is how your server knows to only accept requests that are
   actually from your Slack
10. Click "Install App" on the left nav under "Settings"
11. Click "Install App to Team"
12. Click "Authorize"
13. Try out `/predict help` in a channel.

## Development

To set up a new local clone for development, do this once:

    git clone git@github.com:waveremit/predictions
    cd predictions
    source virtualenv.sh

Then, `workon predictions` will take you into the proper environment. If there
have been changes to the requirements file, run `pip install -r requirements
.txt`.

## Deployment

Within Wave, PRs are auto-deployed to Heroku after merging to master if they
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
