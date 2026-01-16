import pytest
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient
from decimal import Decimal
from django.utils import timezone

from pix.models import PixMessage, Stream


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def mock_redis():
    with patch('pix.services.redis') as mock:
        client = MagicMock()
        client.get.return_value = None
        client.incr.return_value = 1
        client.decr.return_value = 0
        mock.from_url.return_value = client
        yield client