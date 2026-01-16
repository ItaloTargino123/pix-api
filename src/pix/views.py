from django.conf import settings
from faker import Faker
from rest_framework import status
from rest_framework.response import Response



from .serializers import PixMessageSerializer

fake = Faker('pt_BR')


def get_message_limit(request) -> int:
    """Retorna limite de mensagens baseado no header Accept ou query param."""
    accept = request.headers.get('Accept', '')
    format_param = request.query_params.get('format', '')
    
    if 'multipart/json' in accept or format_param == 'multipart':
        return settings.PIX_MAX_MESSAGES_PER_REQUEST
    return 1

def build_response(messages, ispb, stream_id, is_multipart):
    """Constrói response com headers corretos."""
    serializer = PixMessageSerializer(messages, many=True)
    
    if messages:
        data = serializer.data if is_multipart else serializer.data[0]
        response = Response(data, status=status.HTTP_200_OK)
    else:
        response = Response(status=status.HTTP_204_NO_CONTENT)
    
    response['Pull-Next'] = f'/api/pix/{ispb}/stream/{stream_id}'
    return response