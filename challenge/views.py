# challenge/views.py
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
#####################
# Challenge views   #
#####################

@login_required
def challenge(request):
    return render(request, 'send_challenge.html')