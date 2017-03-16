"""Tests for predictions

To run tests:

    pytest .

These tests depend on a postgres db.  Either you can specify the URL of an
empty db with TEST_DATABASE_URL, or you can let this script delete (if exists)
and create a db called postgres:///predictionstest.
"""

import os
import pytest
import datetime
import subprocess

HOUR = datetime.timedelta(seconds=3600)

assert 'DATABASE_URL' not in os.environ

if 'TEST_DATABASE_URL' in os.environ:
    os.environ['DATABASE_URL'] = os.environ['TEST_DATABASE_URL']
else:
    # No db supplied, make our own.  Drop and recreate.
    _localdb = 'predictionstest'
    command = ['dropdb', _localdb]
    pipes = subprocess.Popen(command, stderr=subprocess.PIPE)
    stdout, stderr = pipes.communicate()
    if pipes.returncode != 0 and b'does not exist' not in stderr:
        raise Exception('"%s" failed with stderr=%s' % (
            ' '.join(command), stderr.strip()))
    subprocess.check_call(['createdb', _localdb])

    os.environ['DATABASE_URL'] = 'postgres:///%s' % _localdb

import app
db = app.db
db.create_all()

@pytest.fixture
def s():
    yield db.session
    db.session.rollback()
    db.session.close()

def run(s, command, *args):
    try:
        user = app.lookup_or_create_user(s, 'test')
        out = command(s, user, *args)
    except Exception:
        # Sessions are also rolled back after each test, but we don't expect
        # failed commands to have any effect on the db (normally handle_request
        # deals with this).
        s.rollback()
        raise
    return out

def run_error(s, error, command, *args):
    with pytest.raises(app.PredictionsError) as e:
        run(s, command, *args)
    assert error in str(e.value)

def test_create(s):
    out = run(s, app.create, 'test-contract1', 'terms', '1 hour', '.5')
    assert 'Created contract' in out

    run_error(s, 'already exists',
              app.create, 'test-contract1', 'terms', '1 hour', '.5')

    run_error(s, 'percentage >= 100%: 50',
              app.create, 'test-contract2', 'terms', '1 hour', '50')

    run_error(s, 'percentage <= 0%: -1',
              app.create, 'test-contract2', 'terms', '1 hour', '-1')

    run_error(s, 'closed at',
              app.create, 'test-contract2', 'terms', '-1s', '.5')

def test_help(s):
    out = run(s, app.help)
    assert '/predict' in out

def test_list(s):
    out = run(s, app.list)
    assert 'no active contracts' in out

    run(s, app.create, 'test-contract1', 'terms', '1 hour', '.5')
    run(s, app.create, 'test-contract2', 'terms', '1 hour', '.5')
    run(s, app.create, 'test-contract3', 'terms', '1 hour', '.5')

    out = run(s, app.list)
    assert '''\
test-contract1
test-contract2
test-contract3''' == out

def test_predict(s):
    run_error(s, 'unknown contract',
              app.predict, 'test-contract1', '.6')

    run(s, app.create, 'test-contract1', 'terms', '1 hour', '.5')
    run(s, app.create, 'test-contract2', 'terms', '1 hour', '.5')

    run(s, app.predict, 'test-contract1', '.6')
    run(s, app.predict, 'test-contract1', '.7')

    run(s, app.predict, 'test-contract2', '60%')

    run(s, app.resolve, 'test-contract1', 'false')

    run_error(s, 'already resolved',
              app.predict, 'test-contract1', '1%')

    # skipping parse-float tests and closed-contract tests, because test_create
    # already coverse these.

def test_resolve(s):
    run_error(s, 'unknown contract',
              app.resolve, 'test-contract1', 'true')

    run(s, app.create, 'test-contract1', 'terms', '1 hour', '.5')
    run(s, app.resolve, 'test-contract1', 'true')

    run_error(s, 'already resolved',
              app.resolve, 'test-contract1', 'true')

    run(s, app.create, 'test-contract2', 'terms', '1 hour', '.5')
    run_error(s, 'Predictions must be resolved to "true" or "false"',
              app.resolve, 'test-contract2', 'cabbage')

    run(s, app.create, 'test-contract3', 'terms', '1 hour', '.5')
    with pytest.raises(app.PredictionsError) as e:
        app.resolve(s, app.lookup_or_create_user(s, 'test2'),
                    'test-contract3', 'true')
    assert 'Only test can resolve test-contract3' in str(e.value)

def test_show(s):
    run_error(s, 'unknown contract',
              app.show, 'test-contract1')
    
    run(s, app.create, 'test-contract1', 'terms', '1 hour', '.5')
    out = run(s, app.show, 'test-contract1')
    assert 'terms (Unresolved)' in out
    assert 'Closes' in out

    user1 = app.lookup_or_create_user(s, 'user1')
    user2 = app.lookup_or_create_user(s, 'user2')
    app.predict(s, user1, 'test-contract1', '.6')
    app.predict(s, user2, 'test-contract1', '.8')
    app.predict(s, user1, 'test-contract1', '.4')
    app.predict(s, user1, 'test-contract1', '.2')
    app.predict(s, user2, 'test-contract1', '.1')
    app.predict(s, user1, 'test-contract1', '.0001')
    run(s, app.resolve, 'test-contract1', 'false')

    out = run(s, app.show, 'test-contract1')
    assert 'terms (Resolved False)' in out
    assert 'Closed' in out
    assert '50.00%   test (' in out
    assert '60.00%   user1 (' in out
    assert '80.00%   user2 (' in out
    assert '40.00%   user1 (' in out
    assert '20.00%   user1 (' in out
    assert '10.00%   user2 (' in out
    assert '0.01%   user1 (' in out
    assert 'scores:' in out
    assert 'user1: 126.84' in out
    assert 'user2: -57.54' in out

    # User 'test' doesn't get lots of points for setting the house odds at 1%
    # and then immediately predicting 99%.
    run(s, app.create, 'test-contract2', 'terms', '1 hour', '.01')
    run(s, app.predict, 'test-contract2', '.99')
    app.predict(s, user1, 'test-contract2', '.9')
    run(s, app.predict, 'test-contract2', '.99')
    run(s, app.resolve, 'test-contract2', 'true')
    out = run(s, app.show, 'test-contract2')
    assert 'test: 9.53' in out
    assert 'user1: -9.53' in out
    
