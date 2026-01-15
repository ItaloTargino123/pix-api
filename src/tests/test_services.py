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


@pytest.mark.django_db
class TestStreamServiceGet:

    def test_get_stream_success(self, service, stream):
        found = service.get_stream(stream.ispb, stream.id)

        assert found == stream

    def test_get_stream_not_found(self, service):
        found = service.get_stream('12345678', 'invalid_id')

        assert found is None

    def test_get_stream_closed_returns_none(self, service, stream):
        stream.status = Stream.STATUS_CLOSED
        stream.save()

        found = service.get_stream(stream.ispb, stream.id)

        assert found is None


@pytest.mark.django_db
class TestStreamServiceClose:

    def test_close_stream_updates_status(self, service, stream, mock_redis):
        service.close_stream(stream)


        stream.refresh_from_db()
        assert stream.status == Stream.STATUS_CLOSED
        assert stream.closed_at is not None
        mock_redis.decr.assert_called_once()

    def test_close_stream_releases_messages(self, service, stream, pending_message, mock_redis):
        pending_message.stream = stream
        pending_message.status = PixMessage.STATUS_DELIVERED
        pending_message.save()

        service.close_stream(stream)

        pending_message.refresh_from_db()
        assert pending_message.status == PixMessage.STATUS_PENDING
        assert pending_message.stream is None

    def test_close_stream_already_closed(self, service, stream, mock_redis):
        stream.status = Stream.STATUS_CLOSED
        stream.save()

        service.close_stream(stream)

        mock_redis.decr.assert_not_called()


@pytest.mark.django_db
class TestStreamServiceFetchMessages:

    def test_fetch_messages_returns_pending(self, service, stream, pending_message):
        messages = service.fetch_messages(stream, limit=1)

        assert len(messages) == 1
        assert messages[0].id == pending_message.id

    def test_fetch_messages_marks_as_delivered(self, service, stream, pending_message):
        service.fetch_messages(stream, limit=1)

        pending_message.refresh_from_db()
        assert pending_message.status == PixMessage.STATUS_DELIVERED
        assert pending_message.stream == stream

    def test_fetch_messages_empty_when_none(self, service, stream):
        messages = service.fetch_messages(stream, limit=1)

        assert messages == []

    def test_fetch_messages_respects_limit(self, service, stream):
        for i in range(5):
            PixMessage.objects.create(
                end_to_end_id=f'E12345678202301011234LIM{i}',
                valor=Decimal('10.00'),
                pagador={'nome': 'Pagador', 'ispb': '00000000'},
                recebedor={'nome': 'Recebedor', 'ispb': '12345678'},
                data_hora_pagamento=timezone.now(),
            )

        messages = service.fetch_messages(stream, limit=3)

        assert len(messages) == 3

    def test_fetch_messages_only_returns_matching_ispb(self, service, stream):
        # Mensagem para outro ISPB
        PixMessage.objects.create(
            end_to_end_id='E99999999202301011234OTHER',
            valor=Decimal('10.00'),
            pagador={'nome': 'Pagador', 'ispb': '00000000'},
            recebedor={'nome': 'Recebedor', 'ispb': '99999999'},
            data_hora_pagamento=timezone.now(),
        )
        # Mensagem para o ISPB correto
        PixMessage.objects.create(
            end_to_end_id='E12345678202301011234MATCH',
            valor=Decimal('20.00'),
            pagador={'nome': 'Pagador', 'ispb': '00000000'},
            recebedor={'nome': 'Recebedor', 'ispb': '12345678'},
            data_hora_pagamento=timezone.now(),
        )

        messages = service.fetch_messages(stream, limit=10)

        assert len(messages) == 1
        assert messages[0].recebedor_ispb == '12345678'
    
    def test_fetch_messages_max_ten_multipart(self, service, stream):
        for i in range(15):
            PixMessage.objects.create(
                end_to_end_id=f'E12345678202301011234MAX{i:02d}',
                valor=Decimal('10.00'),
                pagador={'nome': 'Pagador', 'ispb': '00000000'},
                recebedor={'nome': 'Recebedor', 'ispb': '12345678'},
                data_hora_pagamento=timezone.now(),
            )

        messages = service.fetch_messages(stream, limit=10)

        assert len(messages) == 10

    def test_closed_stream_not_found(self, service, mock_redis):
        stream = Stream.objects.create(ispb='12345678')
        service.close_stream(stream)

        found = service.get_stream('12345678', stream.id)

        assert found is None
