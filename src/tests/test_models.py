import pytest
from pix.models import Stream


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