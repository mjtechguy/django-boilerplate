# Generated manually for SensitiveUserData model with encrypted fields

import uuid

import django.utils.timezone
from django.db import migrations, models

import api.encryption


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0004_impersonationlog"),
    ]

    operations = [
        migrations.CreateModel(
            name="SensitiveUserData",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(default=django.utils.timezone.now, editable=False),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("user_id", models.CharField(db_index=True, max_length=255)),
                (
                    "ssn",
                    api.encryption.EncryptedCharField(
                        blank=True, help_text="Social Security Number (encrypted)", max_length=11
                    ),
                ),
                (
                    "date_of_birth",
                    api.encryption.EncryptedCharField(
                        blank=True,
                        help_text="DOB in YYYY-MM-DD format (encrypted)",
                        max_length=10,
                    ),
                ),
                (
                    "medical_record_number",
                    api.encryption.EncryptedCharField(blank=True, max_length=50),
                ),
                (
                    "diagnosis_codes",
                    api.encryption.EncryptedJSONField(
                        blank=True, default=list, help_text="ICD-10 codes (encrypted)"
                    ),
                ),
                (
                    "medications",
                    api.encryption.EncryptedJSONField(blank=True, default=list),
                ),
                (
                    "notes",
                    api.encryption.EncryptedTextField(
                        blank=True, help_text="Clinical notes (encrypted)"
                    ),
                ),
                (
                    "data_classification",
                    models.CharField(
                        choices=[
                            ("PUBLIC", "Public"),
                            ("INTERNAL", "Internal"),
                            ("CONFIDENTIAL", "Confidential"),
                            ("PHI", "Protected Health Information"),
                            ("PII", "Personally Identifiable Information"),
                        ],
                        default="PHI",
                        max_length=20,
                    ),
                ),
            ],
            options={
                "verbose_name": "Sensitive User Data",
                "verbose_name_plural": "Sensitive User Data",
                "indexes": [
                    models.Index(
                        fields=["user_id", "data_classification"],
                        name="api_sensiti_user_id_4a7b8c_idx",
                    ),
                ],
            },
        ),
    ]
