import pytest
from unittest.mock import MagicMock, patch
from decimal import Decimal
from django.utils import timezone
from asgiref.sync import sync_to_async

from pix.models import Stream, PixMessage
from pix.services import StreamService


@pytest.fixture
def mock_redis():
    with patch('pix.services.redis') as mock:
        client = MagicMock()
        client.get.return_value = None
        client.incr.return_value = 1
        client.decr.return_value = 0
        mock.from_url.return_value = client
        yield client


@pytest.fixture
def service(mock_redis):
    return StreamService()


@pytest.fixture
def stream():
    return Stream.objects.create(ispb='12345678')


@pytest.fixture
def pending_message(stream):
    return PixMessage.objects.create(
        end_to_end_id='E12345678202301011234TEST',
        valor=Decimal('100.00'),
        pagador={'nome': 'Pagador', 'ispb': '00000000'},
        recebedor={'nome': 'Recebedor', 'ispb': '12345678'},
        data_hora_pagamento=timezone.now(),
    )


@pytest.mark.django_db
class TestStreamServiceCreate:

    def test_create_stream_success(self, service, mock_redis):
        stream = service.create_stream('12345678')

        assert stream is not None
        assert stream.ispb == '12345678'
        assert stream.status == Stream.STATUS_ACTIVE
        mock_redis.incr.assert_called_once()

    def test_create_stream_limit_reached(self, service, mock_redis):
        mock_redis.get.return_value = b'6'

        stream = service.create_stream('12345678')

        assert stream is None
        mock_redis.incr.assert_not_called()

