# Generated by Django 4.2.3 on 2023-09-02 20:34

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Fence',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('row', models.PositiveSmallIntegerField()),
                ('col', models.PositiveSmallIntegerField()),
                ('fence_type', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='PawnMove',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('row', models.PositiveSmallIntegerField()),
                ('col', models.PositiveSmallIntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='Player',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('row', models.PositiveSmallIntegerField()),
                ('col', models.PositiveSmallIntegerField()),
                ('color', models.PositiveSmallIntegerField()),
                ('remaining_fences', models.PositiveSmallIntegerField(default=10)),
                ('delta_rating', models.FloatField(default=None, null=True)),
                ('delta_deviation', models.FloatField(default=None, null=True)),
                ('delta_volatility', models.FloatField(default=None, null=True)),
                ('rating', models.FloatField(default=None, null=True)),
                ('rating_deviation', models.FloatField(default=None, null=True)),
                ('rating_volatility', models.FloatField(default=None, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='UserDetails',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('standard_rating', models.FloatField()),
                ('standard_rating_deviation', models.FloatField()),
                ('standard_rating_volatility', models.FloatField()),
                ('online', models.SmallIntegerField(default=0)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='QuoridorGame',
            fields=[
                ('game_id', models.SlugField(blank=True, editable=False, primary_key=True, serialize=False, unique=True)),
                ('active_player', models.PositiveSmallIntegerField(default=0)),
                ('game_time', models.DateTimeField(auto_now_add=True)),
                ('rated', models.PositiveSmallIntegerField(default=1)),
                ('move_number', models.PositiveSmallIntegerField(default=0)),
                ('winning_player', models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='game.player')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='player',
            name='game',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='game.quoridorgame'),
        ),
        migrations.AddField(
            model_name='player',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name='Move',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('move_number', models.PositiveSmallIntegerField(default=0)),
                ('fence', models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='fence', to='game.fence')),
                ('game', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='game.quoridorgame')),
                ('pawn_move', models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='pawn', to='game.pawnmove')),
            ],
        ),
        migrations.AddField(
            model_name='fence',
            name='game',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='game.quoridorgame'),
        ),
    ]
