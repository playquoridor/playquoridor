from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from game.models import UserDetails


# Create your forms here.

class NewUserForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        user = super(NewUserForm, self).save(commit=False)
        user.email = self.cleaned_data['email']
        user.is_active = False
        ud = UserDetails(user=user)  # standard_rating=1500, standard_rating_deviation=350, standard_rating_volatility=0.06
        if commit:
            user.save()
            ud.save()
        return user

class AuthNewUserForm(forms.ModelForm):
    # email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username",)

    def save(self, commit=True):
        assert self.email is not None, 'Email must be set'
        user = super(AuthNewUserForm, self).save(commit=False)
        user.set_unusable_password()
        user.email = self.email  # self.cleaned_data['email']
        user.is_active = True
        ud = UserDetails(user=user)  # standard_rating=1500, standard_rating_deviation=350, standard_rating_volatility=0.06
        if commit:
            user.save()
            ud.save()
        return user