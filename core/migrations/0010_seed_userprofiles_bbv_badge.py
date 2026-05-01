from django.db import migrations


def create_profiles_and_bbv_badge(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    UserProfile = apps.get_model('core', 'UserProfile')
    Badge = apps.get_model('core', 'Badge')

    # Ensure every existing user has a profile
    for user in User.objects.all():
        UserProfile.objects.get_or_create(user=user)

    # Create the Certified BBV badge if it doesn't exist
    Badge.objects.get_or_create(
        name='Certified Business Builder Volunteer',
        defaults={
            'description': (
                'Awarded to volunteers who have completed at least one company visit '
                'in each of the last 3 consecutive calendar months.'
            ),
            'icon':           'bi-patch-check-fill',
            'color':          '#014684',
            'criteria_type':  'manual',
            'criteria_value': 0,
            'sort_order':     0,
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_userprofile'),
    ]

    operations = [
        migrations.RunPython(create_profiles_and_bbv_badge, migrations.RunPython.noop),
    ]
