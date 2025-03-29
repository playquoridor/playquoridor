from django.shortcuts import render, redirect
from .forms import NewUserForm, AuthNewUserForm
from django.contrib.auth import login
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import HttpResponse

from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import EmailMessage
# from django.contrib.sites.models import Site
from .tokens import account_activation_token

# Google authentication
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from google.oauth2 import id_token
from google.auth.transport import requests
import os
from django.conf import settings



# Ref: https://ordinarycoders.com/blog/article/django-user-register-login-logout
# Ref: https://pylessons.com/django-email-confirm
def register_request(request):
    if request.method == 'POST':
        form = NewUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            # user.is_active = False
            # user.save()
            # login(request, user)
            # messages.success(request, 'Registration successful')
            activate_email(request, user, form.cleaned_data.get('email'))
            return redirect('index')
        else:
            errors = form.errors  # .replace('password2', 'password')
            if 'password2' in errors and not 'password' in errors:
                errors['password'] = errors.pop('password2')
            # errors['title'] = 'Errors:'
            messages.error(request, errors)  # 'Unsuccessful registration. Invalid information.'
    form = NewUserForm()
    return render(request=request, template_name='register/register.html', context={'register_form': form})


def activate_email(request, user, to_email):
    mail_subject = 'Activate your PlayQuoridor account'
    message = render_to_string('register/activate_account.html', {
        'user': user,
        'domain': get_current_site(request).domain,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': account_activation_token.make_token(user),
        'protocol': 'https' if request.is_secure() else 'http'
    })
    # print('Current site', current_site.domain)
    email = EmailMessage(mail_subject, message, to=[to_email])
    if email.send():
        messages.success(request, f"We've sent you an email. Please click on the received link to complete the registration")
    else:
        messages.error(request, f'Problem sending confirmation email to {to_email}, please check if you typed it correctly')


def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        print('Uid: ', uid, 'uidb64', uidb64)
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    print('Activate user: ', user)

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user)
        messages.success(request, "Your account has been activated")
    else:
        messages.error(request, 'Activation link is invalid')

    return redirect('index')


"""
def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        myuser = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        myuser = None

    if myuser is not None and generate_token.check_token(myuser, token):
        myuser.is_active = True
        myuser.save()
        login(request, myuser)
        messages.success(request, "Your account has been activated")
        return redirect('index')
    else:
        return render(request, 'activation_failed.html')
"""

def set_username_request(request):
    user_data = request.session.get('user_data')
    if not user_data:
        messages.error(request, "Session expired or invalid request.")
        return redirect('index')

    email = user_data['email']
    if not email:
        messages.error(request, "Session expired or invalid request.")
        return redirect('index')
    
    token = request.session.get('google_credential')
    try:
        user_data = id_token.verify_oauth2_token(
            token, requests.Request(), settings.GOOGLE_OAUTH_CLIENT_ID
        )

        # Verify Google as the issuer
        if user_data['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            messages.error(request, 'Invalid token issuer.')
            return redirect('index')

        # Validate that Google issued this token for your app
        if user_data['aud'] != settings.GOOGLE_OAUTH_CLIENT_ID:
            messages.error(request, 'Invalid authentication attempt.')
            return redirect('index')
        
    except ValueError:
        messages.error(request, 'Google authentication failed.')
        return redirect('index')

    if request.method == 'POST':
        # Check if user exists
        existing_user = User.objects.filter(email=email).first()
        if existing_user:
            login(request, existing_user)
            messages.success(request, 'Successfully logged in.')
            return redirect('index')

        form = AuthNewUserForm(request.POST, initial={'email': email})
        form.email = email
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful')
            return redirect('index')
        else:
            errors = form.errors  # .replace('password2', 'password')
            messages.error(request, errors)  # 'Unsuccessful registration. Invalid information.'
    form = AuthNewUserForm(initial={'email': email})
    return render(request=request, template_name='register/register.html', context={'register_form': form})


# @csrf_protect
@csrf_exempt
def auth_receiver(request):
    """
    Google calls this URL after the user has signed in with their Google account.
    """
    # Ref google token: https://developers.google.com/identity/gsi/web/guides/verify-google-id-token?hl=es-419
    csrf_token_cookie = request.COOKIES.get('g_csrf_token')
    if not csrf_token_cookie:
        messages.error(request, 'No CSRF token in cookies.')
        return redirect('index')
    csrf_token_body = request.POST['g_csrf_token']
    if not csrf_token_body:
        messages.error(request, 'No CSRF token in post body.')
        return redirect('index')
    if csrf_token_cookie != csrf_token_body:
        messages.error(request, 'Failed to verify double submit cookie.')
        return redirect('index')

    token = request.POST['credential']

    try:
        user_data = id_token.verify_oauth2_token(
            token, requests.Request(), settings.GOOGLE_OAUTH_CLIENT_ID
        )

        # Verify Google as the issuer
        if user_data['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            messages.error(request, 'Invalid token issuer.')
            return redirect('index')

        # Validate that Google issued this token for your app
        if user_data['aud'] != settings.GOOGLE_OAUTH_CLIENT_ID:
            messages.error(request, 'Invalid authentication attempt.')
            return redirect('index')
        
    except ValueError:
        messages.error(request, 'Google authentication failed.')
        return redirect('index')

    email = user_data.get('email')
    if not email:
        messages.error(request, 'Google did not provide an email.')
        return redirect('index')
    
    # Check if user already exists
    user = User.objects.filter(email=email).first()
    if user:
        login(request, user)
        messages.success(request, 'Successfully logged in.')
        return redirect('index')

    request.session['user_data'] = user_data
    request.session['google_credential'] = token
    # return set_username_request(request, email=user_data['email'])
    return redirect('register:set-username-request')  # Use URL name
