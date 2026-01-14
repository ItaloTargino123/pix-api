import pytest
from decimal import Decimal
from django.utils import timezone
from pix.models import Stream, PixMessage


@pytest.mark.django_db
class TestStream:

    def test_create_stream_generates_id(self):
        stream = Stream.objects.create(ispb='12345678')
        assert stream.id is not None
        assert len(stream.id) == 12

    def test_create_stream_default_status_is_active(self):
        stream = Stream.objects.create(ispb='12345678')
        assert stream.status == Stream.STATUS_ACTIVE

    def test_create_stream_saves_ispb(self):
        stream = Stream.objects.create(ispb='87654321')
        assert stream.ispb == '87654321'

    def test_stream_str(self):
        stream = Stream.objects.create(ispb='12345678')
        assert stream.ispb in str(stream)


@pytest.mark.django_db
class TestPixMessage:

    def test_create_message_generates_uuid(self):
        msg = PixMessage.objects.create(
            end_to_end_id='E12345678202301011234ABC',
            valor=Decimal('100.50'),
            pagador={'nome': 'Pagador', 'ispb': '00000000'},
            recebedor={'nome': 'Recebedor', 'ispb': '12345678'},
            data_hora_pagamento=timezone.now(),
        )
        assert msg.id is not None

    def test_create_message_default_status_is_pending(self):
        msg = PixMessage.objects.create(
            end_to_end_id='E12345678202301011234DEF',
            valor=Decimal('50.00'),
            pagador={'nome': 'Pagador', 'ispb': '00000000'},
            recebedor={'nome': 'Recebedor', 'ispb': '12345678'},
            data_hora_pagamento=timezone.now(),
        )
        assert msg.status == PixMessage.STATUS_PENDING

    def test_recebedor_ispb_auto_populated(self):
        msg = PixMessage.objects.create(
            end_to_end_id='E12345678202301011234GHI',
            valor=Decimal('200.00'),
            pagador={'nome': 'Pagador', 'ispb': '00000000'},
            recebedor={'nome': 'Recebedor', 'ispb': '99999999'},
            data_hora_pagamento=timezone.now(),
        )
        assert msg.recebedor_ispb == '99999999'

    def test_message_str(self):
        msg = PixMessage.objects.create(
            end_to_end_id='E12345678202301011234JKL',
            valor=Decimal('150.00'),
            pagador={'nome': 'Pagador', 'ispb': '00000000'},
            recebedor={'nome': 'Recebedor', 'ispb': '12345678'},
            data_hora_pagamento=timezone.now(),
        )
        assert msg.end_to_end_id in str(msg)
