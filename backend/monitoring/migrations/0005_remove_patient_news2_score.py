from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("monitoring", "0004_patient_last_real_vitals_ms"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="patient",
            name="news2_score",
        ),
    ]
