from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("django_agent", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="message",
            name="thought_signature",
            field=models.TextField(blank=True),
        ),
    ]
