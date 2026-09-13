from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('detect', '0005_pest_information_source'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pest',
            name='pesticide_name',
            field=models.TextField(blank=True, null=True),
        ),
    ]
