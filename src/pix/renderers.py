from rest_framework.renderers import JSONRenderer


class MultipartJSONRenderer(JSONRenderer):
    media_type = 'multipart/json'
    format = 'multipart'
