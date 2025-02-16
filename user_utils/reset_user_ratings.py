from django.contrib.auth.models import User
from game.models import UserDetails

# Running this script:
# python manage.py shell < user_utils/reset_user_ratings.py

if __name__ == '__main__':
    users = User.objects.all()
    for user in users:
        # Glicko-2 initialisation: http://www.glicko.net/glicko/glicko2.pdf
        ud = UserDetails(user=user,
                         standard_rating=1500,
                         standard_rating_deviation=350,
                         standard_rating_volatility=0.06)
        ud.save()

        user.userdetails = ud
        user.save()
