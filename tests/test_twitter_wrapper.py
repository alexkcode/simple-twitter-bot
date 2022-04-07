import pytest
import twitter

@pytest.fixture()
def tww():
    return twitter.TwitterWrapper(
        db=None, 
        api=None, 
        sheets=None, 
        user_id=None
    )

@pytest.fixture()
def follower_good():
    follower = {
        'created_at': 'Mon Nov 29 21:18:15 +0000 2010',
        'statuses_count': 21,
        'followers_count': 1
    }
    return follower

@pytest.fixture()
def follower_bad():
    follower = {
        'created_at': 'Mon Nov 29 21:18:15 +0000 2010',
        'statuses_count': 0,
        'followers_count': 0
    }
    return follower

def test_filter_inactive(follower_good, follower_bad, tww):
    assert tww.filter_inactive(follower_good)
    assert not tww.filter_inactive(follower_bad)
