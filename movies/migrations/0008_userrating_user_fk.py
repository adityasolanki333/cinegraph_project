from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def populate_user_fk(apps, schema_editor):
    UserRating = apps.get_model('movies', 'UserRating')
    User = apps.get_model('auth', 'User')
    valid_user_ids = set(User.objects.values_list('id', flat=True))
    to_delete = []
    to_update = []
    for rating in UserRating.objects.all():
        try:
            uid = int(rating.user_id)
        except (ValueError, TypeError):
            to_delete.append(rating.pk)
            continue
        if uid not in valid_user_ids:
            to_delete.append(rating.pk)
        else:
            rating.user_fk_id = uid
            to_update.append(rating)
    if to_delete:
        UserRating.objects.filter(pk__in=to_delete).delete()
    if to_update:
        UserRating.objects.bulk_update(to_update, ['user_fk_id'], batch_size=500)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('movies', '0007_remove_tmdbmoviecache_genre_ids_and_more'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='userrating',
            unique_together=set(),
        ),
        migrations.AddField(
            model_name='userrating',
            name='user_fk',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='movie_ratings_temp',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(populate_user_fk, noop),
        migrations.RemoveField(
            model_name='userrating',
            name='user_id',
        ),
        migrations.RenameField(
            model_name='userrating',
            old_name='user_fk',
            new_name='user',
        ),
        migrations.AlterField(
            model_name='userrating',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='movie_ratings',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterUniqueTogether(
            name='userrating',
            unique_together={('user', 'movie')},
        ),
    ]
