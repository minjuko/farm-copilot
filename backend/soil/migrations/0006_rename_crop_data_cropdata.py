from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("soil", "0005_crop_data_fertilizer_data_crop_data_soil_data"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RenameModel(
                    old_name="crop_data",
                    new_name="CropData",
                ),
                migrations.AlterModelTable(
                    name="cropdata",
                    table="soil_crop_data",
                ),
            ],
        ),
    ]
