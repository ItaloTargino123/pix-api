from django.db import models
from nanoid import generate
import uuid

def generate_id():
    return generate(size=12)


class Stream(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_CLOSED = "closed"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_CLOSED, "Closed"),
    ]

    id = models.CharField(
        primary_key=True, max_length=20, default=generate_id
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


class PixMessage(models.Model):
    STATUS_PENDING = "pending"
    STATUS_DELIVERED = "delivered"
    STATUS_CONFIRMED = "confirmed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_DELIVERED, "Delivered"),
        (STATUS_CONFIRMED, "Confirmed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    end_to_end_id = models.CharField(max_length=50, unique=True, db_index=True)
    valor = models.DecimalField(max_digits=15, decimal_places=2)

    pagador = models.JSONField()
    recebedor = models.JSONField()

    campo_livre = models.TextField(blank=True, default="")
    tx_id = models.CharField(max_length=35, blank=True, default="")
    data_hora_pagamento = models.DateTimeField()

    recebedor_ispb = models.CharField(max_length=8, db_index=True)
    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True
    )

    stream = models.ForeignKey(
        Stream,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True,
        related_name="messages",
    )

    locked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pix_message"
        indexes = [
            models.Index(fields=["recebedor_ispb", "status"]),
            models.Index(fields=["status", "stream"]),
        ]

    def __str__(self):
        return f"PIX {self.end_to_end_id} - R${self.valor}"

    def save(self, *args, **kwargs):
        if self.recebedor and "ispb" in self.recebedor:
            self.recebedor_ispb = self.recebedor["ispb"]
        super().save(*args, **kwargs)
