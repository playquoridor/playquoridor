# chat/routing.py
from django.urls import re_path

from . import matchmaking_consumer

# Run redis: redis-server --port 6379

websocket_urlpatterns = [
    # re_path(r"ws/matchmaking/(?P<username>\w+)/$", matchmaking_consumer.MatchMakingConsumer.as_asgi()),
    re_path(r"ws/matchmaking/(?P<connection_type>[0-1]{1})/(?P<group_name>[a-zA-Z0-9_]+)/$", matchmaking_consumer.MatchMakingConsumer.as_asgi()),
]