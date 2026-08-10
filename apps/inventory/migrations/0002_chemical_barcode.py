from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="chemical",
            name="barcode",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddIndex(
            model_name="chemical",
            index=models.Index(fields=["barcode"], name="inventory_c_barcode_idx"),
        ),
    ]
