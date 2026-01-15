from rest_framework.renderers import JSONRenderer


class MultipartJSONRenderer(JSONRenderer):
    """Renderer que aceita multipart/json."""
    media_type = 'multipart/json'
    format = 'multipart'
