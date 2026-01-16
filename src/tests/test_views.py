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


@pytest.mark.django_db
class TestGenerateMessages:

    def test_generate_messages_success(self, client):
        response = client.post('/api/pix/util/msgs/12345678/5/')

        assert response.status_code == 201
        assert response.data['created'] == 5
        assert response.data['ispb'] == '12345678'
        assert len(response.data['messages']) == 5
        assert PixMessage.objects.count() == 5

    def test_generate_messages_invalid_ispb_non_numeric(self, client):
        response = client.post('/api/pix/util/msgs/abcdefgh/5/')

        assert response.status_code == 400
        assert 'error' in response.data