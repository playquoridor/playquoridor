# chat/routing.py
from django.urls import re_path

from . import game_consumer

# Run redis: redis-server --port 6379

websocket_urlpatterns = [
    re_path(r"ws/game/(?P<game_id>\w+)/$", game_consumer.GameConsumer.as_asgi()),
]