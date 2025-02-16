# challenge/urls.py
from django.urls import path

from . import views

app_name = 'challenge'
urlpatterns = [
    path('', views.challenge, name='challenge'),
]