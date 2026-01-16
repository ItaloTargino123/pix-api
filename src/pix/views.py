from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.utils import timezone
from django.conf import settings
from faker import Faker
from adrf.decorators import api_view as async_api_view
from asgiref.sync import sync_to_async

from .models import PixMessage
from .services import StreamService
from .serializers import PixMessageSerializer

fake = Faker('pt_BR')


def get_message_limit(request) -> int:
    accept = request.headers.get('Accept', '')
    format_param = request.query_params.get('format', '')
    
    if 'multipart/json' in accept or format_param == 'multipart':
        return settings.PIX_MAX_MESSAGES_PER_REQUEST
    return 1

def build_response(messages, ispb, stream_id, is_multipart):
    serializer = PixMessageSerializer(messages, many=True)
    
    if messages:
        data = serializer.data if is_multipart else serializer.data[0]
        response = Response(data, status=status.HTTP_200_OK)
    else:
        response = Response(status=status.HTTP_204_NO_CONTENT)
    
    response['Pull-Next'] = f'/api/pix/{ispb}/stream/{stream_id}'
    return response



@extend_schema(
    summary='Inicia um novo stream de coleta de mensagens PIX',
    parameters=[
        OpenApiParameter(name='ispb', type=str, location='path', description='ISPB (8 dígitos)'),
        OpenApiParameter(
            name='Accept',
            type=str,
            location='header',
            description='application/json (1 msg) ou multipart/json (até 10 msgs)',
            required=False,
        ),
    ],
    responses={
        200: {'description': 'Mensagens disponíveis'},
        204: {'description': 'Sem mensagens disponíveis'},
        400: {'description': 'ISPB inválido'},
        429: {'description': 'Limite de streams atingido'},
    },
    tags=['PIX Stream'],
)
@async_api_view(['GET'])
async def stream_start(request, ispb: str):    
    if not ispb.isdigit() or len(ispb) != 8:
        return Response(
            {'error': 'ISPB deve ter 8 dígitos'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    service = StreamService()
    stream = await sync_to_async(service.create_stream)(ispb)
    
    if not stream:
        return Response(
            {'error': 'Limite de streams simultâneos atingido'},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    
    limit = get_message_limit(request)
    is_multipart = limit > 1
    messages = await service.fetch_messages_with_polling(stream, limit)
    
    return build_response(messages, ispb, stream.id, is_multipart)


@extend_schema(
    summary='Continua leitura ou fecha stream',
    parameters=[
        OpenApiParameter(name='ispb', type=str, location='path', description='ISPB (8 dígitos)'),
        OpenApiParameter(name='interation_id', type=str, location='path', description='ID do stream'),
        OpenApiParameter(
            name='Accept',
            type=str,
            location='header',
            description='application/json (1 msg) ou multipart/json (até 10 msgs)',
            required=False,
        ),
    ],
    responses={
        200: {'description': 'Mensagens disponíveis ou stream fechado'},
        204: {'description': 'Sem mensagens disponíveis'},
        400: {'description': 'ISPB inválido'},
        404: {'description': 'Stream não encontrado'},
    },
    tags=['PIX Stream'],
)
@async_api_view(['GET', 'DELETE'])
async def stream_continue(request, ispb: str, interation_id: str):
    """Continua leitura (GET) ou fecha stream (DELETE)."""
    
    if not ispb.isdigit() or len(ispb) != 8:
        return Response(
            {'error': 'ISPB deve ter 8 dígitos'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    service = StreamService()
    stream = await sync_to_async(service.get_stream)(ispb, interation_id)
    
    if not stream:
        return Response(
            {'error': 'Stream não encontrado'},
            status=status.HTTP_404_NOT_FOUND,
        )
    
    if request.method == 'DELETE':
        await sync_to_async(service.close_stream)(stream)
        return Response({}, status=status.HTTP_200_OK)
    
    # GET - busca mensagens
    limit = get_message_limit(request)
    is_multipart = limit > 1
    messages = await service.fetch_messages_with_polling(stream, limit)
    
    return build_response(messages, ispb, stream.id, is_multipart)
