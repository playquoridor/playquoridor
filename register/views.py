from django.shortcuts import render, redirect
from .forms import NewUserForm
from django.contrib.auth import login
from django.contrib import messages
from django.contrib.auth.models import User

from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import EmailMessage
# from django.contrib.sites.models import Site

from .tokens import account_activation_token

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