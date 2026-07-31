from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        # Add new fields to UserProfile
        migrations.AddField(
            model_name='userprofile',
            name='address',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='dietary_preferences',
            field=models.JSONField(blank=True, default=list),
        ),
        # Create Restaurant model
        migrations.CreateModel(
            name='Restaurant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('brand', models.CharField(blank=True, max_length=200, null=True)),
                ('cuisine', models.CharField(max_length=100)),
                ('type', models.CharField(max_length=100)),
                ('description', models.TextField()),
                ('owner_name', models.CharField(max_length=100)),
                ('phone', models.CharField(max_length=20)),
                ('email', models.EmailField(max_length=150, unique=True)),
                ('address', models.TextField()),
                ('city', models.CharField(max_length=100)),
                ('state', models.CharField(max_length=100)),
                ('open_time', models.TimeField(blank=True, null=True)),
                ('close_time', models.TimeField(blank=True, null=True)),
                ('prep_time', models.IntegerField(help_text='Prep time in minutes')),
                ('delivery_radius_km', models.IntegerField()),
                ('seating_capacity', models.IntegerField(blank=True, null=True)),
                ('gstin', models.CharField(blank=True, default='', max_length=50)),
                ('fssai', models.CharField(max_length=50)),
                ('source', models.CharField(blank=True, default='', max_length=100)),
                ('dietary_options_offered', models.JSONField(blank=True, default=list)),
                ('channels_to_activate', models.JSONField(blank=True, default=list)),
                ('payment_methods_offered', models.JSONField(blank=True, default=list)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
