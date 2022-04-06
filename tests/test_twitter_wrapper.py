import pytest
from app.bots.twitter import TwitterWrapper

@pytest.fixture()
def tww():
    return TwitterWrapper(
        db=None, 
        api=None, 
        sheets=None, 
        user_id=None
    )

@pytest.fixture()
def follower(tww):
    follower = {
        'created_at': 'Mon Nov 29 21:18:15 +0000 2010',
        'statuses_count': 1,
        'followers_count': 1
    }
    return follower

def test_filter_inactive(follower):
    filtered = tww.filter_inactive(follower)
    assert filtered