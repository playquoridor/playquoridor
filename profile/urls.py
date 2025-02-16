# challenge/urls.py
from django.urls import path
from django.urls import re_path  # https://stackoverflow.com/questions/59115733/how-to-make-trailing-slash-optional-in-django

from . import views

app_name = 'user'
urlpatterns = [
    path('<username>/games/', views.list_games, name='list_games'),
    path('<username_1>/games/<username_2>/', views.list_user_user_games, name='list_user_user_games'),
    path('<username>/', views.show_profile, name='show_profile'),
]