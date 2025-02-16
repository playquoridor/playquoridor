from django.contrib.auth.models import User
from game.models import UserDetails

# CREATE USER
# https://stackoverflow.com/questions/10372877/how-to-create-a-user-in-django
# from django.contrib.auth.models import User
# user = User.objects.create_user(username='john',
#                                  email='jlennon@beatles.com',
#                                  password='glass onion')

# Running this script:
# python manage.py shell < user_utils/create_user.py

# if __name__ == '__main__':
username = input('Username: ')
password = input('Password: ')

user = User.objects.create_user(username=username, password=password)
user.save()

ud = UserDetails(user=user, standard_rating=1500, standard_rating_deviation=350, standard_rating_volatility=0.06)
ud.save()