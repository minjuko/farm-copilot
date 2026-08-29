from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('detect', '0003_alter_pestdetection_detection_date_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='pest',
            name='code',
            field=models.CharField(
                blank=True,
                max_length=100,
                null=True,
                unique=True,
            ),
        ),
        migrations.CreateModel(
            name='PestModelClass',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('class_id', models.PositiveIntegerField(unique=True)),
                ('model_label', models.CharField(max_length=100)),
                ('pest', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='model_classes', to='detect.pest')),
            ],
            options={
                'db_table': 'pest_model_class',
                'ordering': ['class_id'],
            },
        ),
    ]
