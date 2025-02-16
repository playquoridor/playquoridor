# Instructions for installing the server (Ubuntu 22.04)

## Installation
Install pip
```
sudo apt install python3-pip
```

Install Python libraries
```
pip install django
python3 -m pip install -U channels["daphne"]
pip install django-crispy-forms
pip install crispy-bootstrap4
pip install pyquoridor
pip install pandas
pip install channels-redis
pip install psycopg2-binary
```

Install redis-server
```
sudo apt install redis-server
```

## PostgreSQL database (optional)

Install [PostgreSQL](https://www.postgresql.org/download/linux/ubuntu/)
```
# Create the file repository configuration:
sudo sh -c 'echo "deb https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'

# Import the repository signing key:
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -

# Update the package lists:
sudo apt-get update

# Install the latest version of PostgreSQL.
# If you want a specific version, use 'postgresql-12' or similar instead of 'postgresql':
sudo apt-get -y install postgresql
```

Start PostgreSQL
```
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

Create database and user
```
# Access PostgreSQL from command line
sudo -i -u postgres

psql
> CREATE DATABASE quoridor_db;
> CREATE USER <user> WITH ENCRYPTED PASSWORD <password>;
> ALTER ROLE <user> SET client_encoding TO 'utf8';
> ALTER ROLE <user> SET default_transaction_isolation TO 'read committed';
> ALTER ROLE <user> SET timezone TO 'UTC';
> GRANT ALL PRIVILEGES ON DATABASE quoridor_db TO <user>;
```

We recommend using `user=postgres`. The password can be set as follows:
```
sudo -u postgres psql
\password
```

Create PostgreSQL conf
```
> ~/.pg_service.conf 
[my_service]
host=localhost
user=<user>
dbname=quoridor_db
port=5432
```

Create PostgreSQL login details (`.my_pgpass`) in root of Django project
```
> .my_pgpass
localhost:5432:quoridor_db:<user>:<password>
```

Change permissions of `my_pgpass`
```
chmod 0600 .my_pgpass
```

If using PostgreSQL, change the default database in `quoridor/settings.py` (currently commented out).

## Setup database

Create database
```
python3 manage.py makemigrations game
python3 manage.py migrate
```

## Creating users

Users can be created as follows:
```
> python3 manage.py shell
from django.contrib.auth.models import User
from game.models import UserDetails

user = User.objects.create_user(username='test_user', password='test')
ud = UserDetails(user=user)
ud.save()
```

## Email backend for user registration (optional)

Set up email backend (for sending user activation emails). In `settings.py` modify the following information
```
# Email backend
# https://developer.mozilla.org/en-US/docs/Learn/Server-side/Django/Authentication
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_FROM = '<email>'
EMAIL_HOST_USER = '<email>'
EMAIL_HOST_PASSWORD = '<16 character token>'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
PASSWORD_RESET_TIMEOUT = 3600
```

For local testing only (no deployment): create the `127.0.0.1:8000` sites
```
> python3 manage.py shell
from django.contrib.sites.models import Site

new_site = Site.objects.create(domain='localhost:8000', name='localhost:8000')
new_site = Site.objects.create(domain='127.0.0.1:8000', name='127.0.0.1:8000')
```

The sites can also be managed with a superuser via `https://127.0.0.1:8000/admin/sites/site/`

## Running the server

Run redis
```
redis-server --port 6379
```

Run matchmaking master in a separate process
```
python3 -m matchmaking.matchmaking_master matchmaking_master.py
```

Run server
```
python manage.py runserver
```