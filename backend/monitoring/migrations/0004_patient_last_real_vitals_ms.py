from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("monitoring", "0003_device_hl7_nat_source_ip"),
    ]

    operations = [
        migrations.AddField(
            model_name="patient",
            name="last_real_vitals_ms",
            field=models.BigIntegerField(blank=True, null=True),
        ),
    ]
