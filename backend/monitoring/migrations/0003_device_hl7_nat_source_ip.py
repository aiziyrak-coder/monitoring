from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("monitoring", "0002_device_hl7_sending_application"),
    ]

    operations = [
        migrations.AddField(
            model_name="device",
            name="hl7_nat_source_ip",
            field=models.GenericIPAddressField(blank=True, null=True),
        ),
    ]
