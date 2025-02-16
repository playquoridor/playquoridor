# register/urls.py
from django.urls import path

from . import views

app_name = 'register'
urlpatterns = [
    path('', views.register_request, name='register'),
    path('activate/<uidb64>/<token>', views.activate, name='activate'),
]