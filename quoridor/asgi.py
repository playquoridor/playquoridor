"""
ASGI config for quoridor project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/asgi/
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "quoridor.settings")
# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

import game.routing
import challenge.routing
import matchmaking.routing

url_patterns = game.routing.websocket_urlpatterns +\
               challenge.routing.websocket_urlpatterns +\
               matchmaking.routing.websocket_urlpatterns
print('URL patterns', url_patterns)

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter(url_patterns))
        ),
    }
)

# Ref: https://blog.heroku.com/in_deep_with_django_channels_the_future_of_real_time_apps_in_django
# from channels.layers import get_channel_layer
# channel_layer = get_channel_layer()