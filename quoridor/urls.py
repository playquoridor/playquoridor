"""quoridor URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('challenge/', include('challenge.urls')),
    path('game/', include('game.urls')),
    path('user/', include('profile.urls', namespace='profile')),
    path('register/', include('register.urls')),
    path('tutorial/', include('tutorial.urls')),
    path('community/', views.community, name='community'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('admin/', admin.site.urls),
    path('accounts/login/', auth_views.LoginView.as_view()),
    path('accounts/logout/', auth_views.LogoutView.as_view()),
    path('accounts/', include('django.contrib.auth.urls')),
    # path('accounts/', include('allauth.urls')),  # Include allauth URLs
    # path('accounts/', include('allauth.socialaccount.urls')),
]

handler404 = 'quoridor.views.handler404'
handler500 = 'quoridor.views.handler500'
