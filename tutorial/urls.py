# tutorial/urls.py
from django.urls import path

from . import views

app_name = 'tutorial'
urlpatterns = [
    path('', views.introduction),
    path('introduction', views.introduction, name='introduction'),
]