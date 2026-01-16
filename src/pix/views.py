from django.conf import settings
from faker import Faker

fake = Faker('pt_BR')


def get_message_limit(request) -> int:
    """Retorna limite de mensagens baseado no header Accept ou query param."""
    accept = request.headers.get('Accept', '')
    format_param = request.query_params.get('format', '')
    
    if 'multipart/json' in accept or format_param == 'multipart':
        return settings.PIX_MAX_MESSAGES_PER_REQUEST
    return 1