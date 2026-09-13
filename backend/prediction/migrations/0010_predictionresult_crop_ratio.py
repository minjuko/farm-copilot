from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('prediction', '0009_alter_predictionresult_latest_year'),
    ]

    operations = [
        migrations.AddField(
            model_name='predictionresult',
            name='crop_ratio',
            field=models.FloatField(blank=True, null=True),
        ),
    ]
