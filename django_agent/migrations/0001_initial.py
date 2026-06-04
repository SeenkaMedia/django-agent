from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Conversation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE,
                    related_name="agent_conversation", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="Message",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("user", "user"), ("model", "model"), ("tool", "tool")], max_length=10)),
                ("text", models.TextField(blank=True)),
                ("tool_name", models.CharField(blank=True, max_length=100)),
                ("tool_args", models.JSONField(blank=True, null=True)),
                ("tool_result", models.JSONField(blank=True, null=True)),
                ("status", models.CharField(choices=[("ok", "ok"), ("pending", "pending"), ("rejected", "rejected")],
                    default="ok", max_length=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("conversation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name="messages", to="django_agent.conversation")),
            ],
            options={"ordering": ["id"]},
        ),
        migrations.CreateModel(
            name="ActionLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tool_name", models.CharField(max_length=100)),
                ("args", models.JSONField(blank=True, null=True)),
                ("result", models.JSONField(blank=True, null=True)),
                ("ok", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("conversation", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL,
                    to="django_agent.conversation")),
                ("user", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL,
                    to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-id"]},
        ),
    ]
