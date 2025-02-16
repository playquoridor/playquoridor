# chat/routing.py
from django.urls import re_path

from . import challenge_consumer

# Run redis: redis-server --port 6379

websocket_urlpatterns = [
    re_path(r"ws/challenge/(?P<username>\w+)/$", challenge_consumer.ChallengeConsumer.as_asgi()),
]