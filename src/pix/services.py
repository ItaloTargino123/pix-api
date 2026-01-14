import asyncio
import time

from django.conf import settings
from django.db import transaction
from django.utils import timezone
import redis

from .models import Stream, PixMessage


class StreamService:

    def __init__(self):
        self.redis = redis.from_url(settings.REDIS_URL)
        self.max_streams = settings.PIX_MAX_STREAMS_PER_ISPB

    def _stream_count_key(self, ispb: str) -> str:
        return f'stream:count:{ispb}'

    def get_active_count(self, ispb: str) -> int:
        count = self.redis.get(self._stream_count_key(ispb))
        return int(count) if count else 0

    def create_stream(self, ispb: str) -> Stream | None:
        if self.get_active_count(ispb) >= self.max_streams:
            return None

        stream = Stream.objects.create(ispb=ispb)
        self.redis.incr(self._stream_count_key(ispb))
        return stream

    def get_stream(self, ispb: str, stream_id: str) -> Stream | None:
        try:
            return Stream.objects.get(id=stream_id, ispb=ispb, status=Stream.STATUS_ACTIVE)
        except Stream.DoesNotExist:
            return None

    @transaction.atomic
    def close_stream(self, stream: Stream) -> None:
        if stream.status == Stream.STATUS_CLOSED:
            return

        # Libera mensagens não confirmadas
        PixMessage.objects.filter(
            stream=stream,
            status=PixMessage.STATUS_DELIVERED,
        ).update(
            stream=None,
            status=PixMessage.STATUS_PENDING,
        )

        stream.status = Stream.STATUS_CLOSED
        stream.closed_at = timezone.now()
        stream.save()

        self.redis.decr(self._stream_count_key(stream.ispb))

    @transaction.atomic
    def fetch_messages(self, stream: Stream, limit: int = 1) -> list[PixMessage]:
        messages = list(
            PixMessage.objects
            .select_for_update(skip_locked=True)
            .filter(
                recebedor_ispb=stream.ispb,
                status=PixMessage.STATUS_PENDING,
                stream__isnull=True,
            )
            .order_by('created_at')[:limit]
        )

        if messages:
            ids = [m.id for m in messages]
            PixMessage.objects.filter(id__in=ids).update(
                stream=stream,
                status=PixMessage.STATUS_DELIVERED,
            )
            messages = list(PixMessage.objects.filter(id__in=ids))

        return messages

    async def fetch_messages_with_polling(self, stream: Stream, limit: int = 1) -> list[PixMessage]:
        timeout = settings.PIX_LONG_POLLING_TIMEOUT
        start = time.time()

        while True:
            messages = self.fetch_messages(stream, limit)
            if messages:
                return messages

            if time.time() - start >= timeout:
                return []

            await asyncio.sleep(0.5)
