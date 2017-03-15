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

Pushes to master are auto-deployed to wave-prediction-market.herokuapp.com
