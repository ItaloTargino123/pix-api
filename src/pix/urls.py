from django.urls import path
from .views import generate_messages, stream_start, stream_continue

urlpatterns = [
    # Stream endpoints
    path('<str:ispb>/stream/start', stream_start, name='stream-start'),
    path('<str:ispb>/stream/<str:interation_id>', stream_continue, name='stream-continue'),
    # Utilitários
    path('util/msgs/<str:ispb>/<int:quantity>/', generate_messages, name='generate-messages'),
]
