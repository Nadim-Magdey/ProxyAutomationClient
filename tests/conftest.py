import pytest

class MockInterface:
    def __init__(self):
        self.calls = []

    def add_rule(self, **kwargs):
        self.calls.append(kwargs)

@pytest.fixture
def mock_interface():
    return MockInterface()

@pytest.fixture
def context():
    return {"vars": {}}
