# Source this file to activate the waveussd virtualenv.

if [ -x /usr/local/bin/python3 ]; then
    export VIRTUALENVWRAPPER_PYTHON=/usr/local/bin/python3
else
    export VIRTUALENVWRAPPER_PYTHON=$(which python3)
fi
export WORKON_HOME=~/.virtualenvs
source /usr/local/bin/virtualenvwrapper.sh


if [ -d $WORKON_HOME/predictions ]; then
    workon predictions
else
    echo 'Setting up a new predictions virtualenv.'
    mkvirtualenv predictions
    bin/fixme
    workon predictions
    if which pip3; then pip=pip3; else pip=pip; fi
    $pip install -r requirements.txt
    echo
    echo "You're good to go!"
fi
