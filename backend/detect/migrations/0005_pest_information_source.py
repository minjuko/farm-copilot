from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('detect', '0004_pest_code_and_model_class'),
    ]

    operations = [
        migrations.AddField(
            model_name='pest',
            name='information_source',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='pest',
            name='information_source_url',
            field=models.URLField(blank=True, max_length=500, null=True),
        ),
    ]
