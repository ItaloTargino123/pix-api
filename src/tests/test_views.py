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

    def test_generate_messages_invalid_ispb_wrong_length(self, client):
        response = client.post('/api/pix/util/msgs/123/5/')

        assert response.status_code == 400
        assert 'error' in response.data

    def test_generate_messages_quantity_too_low(self, client):
        response = client.post('/api/pix/util/msgs/12345678/0/')

        assert response.status_code == 400
        assert 'error' in response.data

    def test_generate_messages_quantity_too_high(self, client):
        response = client.post('/api/pix/util/msgs/12345678/101/')

        assert response.status_code == 400
        assert 'error' in response.data

    def test_generate_messages_sets_recebedor_ispb(self, client):
        client.post('/api/pix/util/msgs/99999999/1/')

        msg = PixMessage.objects.first()
        assert msg.recebedor_ispb == '99999999'



@pytest.mark.django_db
class TestStreamStart:

    def test_stream_start_returns_message(self, client, mock_redis):
        PixMessage.objects.create(
            end_to_end_id='E12345678202301011234START',
            valor=Decimal('100.00'),
            pagador={'nome': 'Pagador', 'ispb': '00000000'},
            recebedor={'nome': 'Recebedor', 'ispb': '12345678'},
            data_hora_pagamento=timezone.now(),
        )

        response = client.get('/api/pix/12345678/stream/start')

        assert response.status_code == 200
        assert 'Pull-Next' in response.headers
        assert response.data['endToEndId'] == 'E12345678202301011234START'

    def test_stream_start_invalid_ispb(self, client):
        response = client.get('/api/pix/123/stream/start')

        assert response.status_code == 400

    def test_stream_start_limit_exceeded(self, client, mock_redis):
        mock_redis.get.return_value = b'6'

        response = client.get('/api/pix/12345678/stream/start')

        assert response.status_code == 429


@pytest.mark.django_db
class TestStreamContinue:

    def test_stream_continue_returns_message(self, client, mock_redis):
        stream = Stream.objects.create(ispb='12345678')
        PixMessage.objects.create(
            end_to_end_id='E12345678202301011234CONT',
            valor=Decimal('100.00'),
            pagador={'nome': 'Pagador', 'ispb': '00000000'},
            recebedor={'nome': 'Recebedor', 'ispb': '12345678'},
            data_hora_pagamento=timezone.now(),
        )

        response = client.get(f'/api/pix/12345678/stream/{stream.id}')

        assert response.status_code == 200
        assert 'Pull-Next' in response.headers
    
    def test_stream_continue_not_found(self, client, mock_redis):
        response = client.get('/api/pix/12345678/stream/invalidid')

        assert response.status_code == 404

    def test_stream_delete_success(self, client, mock_redis):
        stream = Stream.objects.create(ispb='12345678')

        response = client.delete(f'/api/pix/12345678/stream/{stream.id}')

        assert response.status_code == 200
        stream.refresh_from_db()
        assert stream.status == Stream.STATUS_CLOSED

    def test_stream_delete_not_found(self, client, mock_redis):
        response = client.delete('/api/pix/12345678/stream/invalidid')

        assert response.status_code == 404
    