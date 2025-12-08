# Generated migration for AuditLog tamper-evidence fields
# Adds HMAC signature, hash-chaining, sequence numbers, and nonce fields

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0005_add_sensitive_user_data"),
    ]

    operations = [
        migrations.AddField(
            model_name="auditlog",
            name="signature",
            field=models.CharField(
                blank=True,
                max_length=128,
                help_text="HMAC-SHA256 signature of this entry",
            ),
        ),
        migrations.AddField(
            model_name="auditlog",
            name="previous_hash",
            field=models.CharField(
                blank=True,
                max_length=128,
                help_text="Hash of previous audit entry for chain integrity",
            ),
        ),
        migrations.AddField(
            model_name="auditlog",
            name="sequence_number",
            field=models.BigIntegerField(
                default=0,
                db_index=True,
                help_text="Sequential entry number for ordering",
            ),
        ),
        migrations.AddField(
            model_name="auditlog",
            name="nonce",
            field=models.CharField(
                blank=True,
                max_length=64,
                help_text="Random nonce for signature uniqueness",
            ),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["sequence_number"], name="api_auditlo_sequenc_idx"),
        ),
    ]
