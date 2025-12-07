"""
Management command to rotate encryption keys.

This command re-encrypts data with the current primary encryption key.
Useful when adding a new key or phasing out an old one.

Usage:
    python manage.py rotate_encryption_keys --model api.SensitiveUserData --field ssn
    python manage.py rotate_encryption_keys --model api.SensitiveUserData --all-fields
    python manage.py rotate_encryption_keys --model api.SensitiveUserData --field ssn --batch-size 100
"""

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from api.encryption import (
    EncryptedCharField,
    EncryptedEmailField,
    EncryptedJSONField,
    EncryptedTextField,
    EncryptionManager,
)


class Command(BaseCommand):
    help = "Rotate encryption keys for encrypted fields"

    def add_arguments(self, parser):
        parser.add_argument(
            "--model",
            type=str,
            required=True,
            help="Model in format app.ModelName (e.g., api.SensitiveUserData)",
        )
        parser.add_argument(
            "--field",
            type=str,
            help="Field name to rotate (e.g., ssn). Use --all-fields to rotate all encrypted fields.",
        )
        parser.add_argument(
            "--all-fields",
            action="store_true",
            help="Rotate all encrypted fields in the model",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Number of records to process per batch (default: 100)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be rotated without actually doing it",
        )

    def handle(self, *args, **options):
        model_path = options["model"]
        field_name = options.get("field")
        all_fields = options.get("all_fields")
        batch_size = options["batch_size"]
        dry_run = options["dry_run"]

        # Validate arguments
        if not field_name and not all_fields:
            raise CommandError("You must specify either --field or --all-fields")

        if field_name and all_fields:
            raise CommandError("You cannot specify both --field and --all-fields")

        # Parse model path
        try:
            app_label, model_name = model_path.split(".")
        except ValueError:
            raise CommandError(
                f"Invalid model path: {model_path}. Use format: app.ModelName"
            )

        # Get model
        try:
            model = apps.get_model(app_label, model_name)
        except LookupError:
            raise CommandError(f"Model {model_path} not found")

        # Get encrypted fields
        encrypted_field_types = (
            EncryptedCharField,
            EncryptedTextField,
            EncryptedJSONField,
            EncryptedEmailField,
        )
        encrypted_fields = [
            field
            for field in model._meta.get_fields()
            if isinstance(field, encrypted_field_types)
        ]

        if not encrypted_fields:
            raise CommandError(f"Model {model_path} has no encrypted fields")

        # Determine which fields to rotate
        if all_fields:
            fields_to_rotate = encrypted_fields
        else:
            # Find the specific field
            field_obj = None
            for field in encrypted_fields:
                if field.name == field_name:
                    field_obj = field
                    break

            if not field_obj:
                available_fields = ", ".join([f.name for f in encrypted_fields])
                raise CommandError(
                    f"Field '{field_name}' is not an encrypted field. "
                    f"Available encrypted fields: {available_fields}"
                )

            fields_to_rotate = [field_obj]

        # Display plan
        field_names = [f.name for f in fields_to_rotate]
        self.stdout.write(
            self.style.SUCCESS(
                f"\nKey Rotation Plan for {model_path}:\n"
                f"  Fields: {', '.join(field_names)}\n"
                f"  Batch size: {batch_size}\n"
                f"  Dry run: {dry_run}\n"
            )
        )

        # Count total records
        total_count = model.objects.count()
        self.stdout.write(f"Total records: {total_count}\n")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes will be made\n"))
            return

        # Initialize encryption manager
        manager = EncryptionManager()

        # Process in batches
        processed = 0
        rotated = 0
        errors = 0

        try:
            # Use iterator() for memory efficiency
            queryset = model.objects.all().iterator(chunk_size=batch_size)

            for record in queryset:
                try:
                    with transaction.atomic():
                        # Track if any field was rotated for this record
                        record_rotated = False

                        # Rotate each field
                        for field in fields_to_rotate:
                            field_name = field.name
                            current_value = getattr(record, field_name)

                            # Skip empty/null values
                            if not current_value:
                                continue

                            try:
                                # Get the encrypted value from DB (bypassing decryption)
                                # We need to work with the raw encrypted value
                                encrypted_value = record.__dict__[field_name]

                                # Rotate the encryption
                                new_encrypted_value = manager.rotate_encryption(encrypted_value)

                                # Only update if the value changed (different key was used)
                                if encrypted_value != new_encrypted_value:
                                    # Update the field directly in __dict__ to avoid re-encryption
                                    record.__dict__[field_name] = new_encrypted_value
                                    record_rotated = True

                            except Exception as e:
                                self.stdout.write(
                                    self.style.ERROR(
                                        f"  Error rotating field '{field_name}' "
                                        f"for record {record.pk}: {e}"
                                    )
                                )
                                raise

                        # Save if any field was rotated
                        if record_rotated:
                            # Use update_fields to only update the rotated fields
                            update_fields = [f.name for f in fields_to_rotate]
                            record.save(update_fields=update_fields)
                            rotated += 1

                        processed += 1

                        # Progress indicator
                        if processed % batch_size == 0:
                            self.stdout.write(
                                f"  Processed: {processed}/{total_count} "
                                f"(Rotated: {rotated})"
                            )

                except Exception as e:
                    errors += 1
                    self.stdout.write(
                        self.style.ERROR(f"  Error processing record {record.pk}: {e}")
                    )
                    # Continue with next record
                    continue

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\n\nInterrupted by user"))
            self.stdout.write(
                f"Processed: {processed}/{total_count}, Rotated: {rotated}, Errors: {errors}"
            )
            return

        # Final summary
        self.stdout.write(
            self.style.SUCCESS(
                f"\n\nRotation complete!\n"
                f"  Total processed: {processed}\n"
                f"  Records rotated: {rotated}\n"
                f"  Errors: {errors}\n"
            )
        )

        if errors > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"\n{errors} errors occurred. Check the output above for details."
                )
            )
