# Predictions

A prediction market

## Setup

To set up a new local clone for development, do this once:

    git clone git@github.com:waveremit/predictions
    cd predictions
    source virtualenv.sh

Then, `workon predictions` will take you into the proper environment. If there
have been changes to the requirements file, run `pip install -r requirements
.txt`.

## Deployment

Within Wave, PRs are auto-deployed to Heroku after merging to master, if they
pass CI.  Outside Wave you're on your own!

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
