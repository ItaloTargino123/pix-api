from rest_framework import serializers
from .models import PixMessage


class PixMessageSerializer(serializers.ModelSerializer):
    endToEndId = serializers.CharField(source='end_to_end_id')
    campoLivre = serializers.CharField(source='campo_livre')
    txId = serializers.CharField(source='tx_id')
    dataHoraPagamento = serializers.DateTimeField(source='data_hora_pagamento')

    class Meta:
        model = PixMessage
        fields = [
            'endToEndId',
            'valor',
            'pagador',
            'recebedor',
            'campoLivre',
            'txId',
            'dataHoraPagamento',
        ]
