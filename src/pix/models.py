
from django.db import models
from nanoid import generate


class Stream(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_CLOSED = "closed"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_CLOSED, "Closed"),
    ]

    id = models.CharField(
        primary_key=True, max_length=20, default=lambda: generate(size=12)
    )
    ispb = models.CharField(max_length=8, db_index=True)
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=STATUS_ACTIVE, db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "pix_stream"
        indexes = [
            models.Index(fields=["ispb", "status"]),
        ]

    def __str__(self):
        return f"Stream {self.id} - {self.ispb} - {self.status}"
