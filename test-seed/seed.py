import django

django.setup()

from django.contrib.auth import get_user_model  # noqa: E402

from api.models import Org, SampleResource, Settings, Team  # noqa: E402
from api.models_local_auth import LocalUserProfile  # noqa: E402

User = get_user_model()


def create_platform_admin():
    """Create a default platform admin user for local authentication."""
    email = "admin@example.com"
    password = "AdminPass123"

    # Check if user already exists
    if User.objects.filter(email=email).exists():
        user = User.objects.get(email=email)
        print(f"Platform admin already exists: {email}")
    else:
        # Create user
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,  # This won't be used - LocalUserProfile handles auth
            first_name="Platform",
            last_name="Admin",
            is_staff=True,
            is_superuser=True,
        )
        print(f"Created platform admin user: {email}")

    # Create or update local profile
    profile, created = LocalUserProfile.objects.get_or_create(
        user=user,
        defaults={
            "roles": ["platform_admin", "user"],
            "email_verified": True,
        }
    )

    if created:
        # Set password using argon2
        profile.set_password(password)
        profile.save()
        print(f"Created local profile for {email} with platform_admin role")
    else:
        # Update roles if profile already exists
        if "platform_admin" not in profile.roles:
            profile.roles = ["platform_admin", "user"]
            profile.save()
            print(f"Updated {email} with platform_admin role")
        else:
            print(f"Local profile already exists for {email}")

    print(f"\n*** Default Platform Admin Credentials ***")
    print(f"    Email: {email}")
    print(f"    Password: {password}")
    print(f"*******************************************\n")

    return user


def main():
    # Create platform admin first
    admin_user = create_platform_admin()

    # Create sample org and team
    org, org_created = Org.objects.get_or_create(
        name="Acme Health",
        defaults={"license_tier": "pro", "feature_flags": {"export": True}}
    )
    if org_created:
        print(f"Created org: {org.name}")
    else:
        print(f"Org already exists: {org.name}")

    team, team_created = Team.objects.get_or_create(
        org=org,
        name="Care Team"
    )
    if team_created:
        print(f"Created team: {team.name}")

    SampleResource.objects.get_or_create(
        org=org,
        team=team,
        name="seed-resource"
    )

    Settings.objects.update_or_create(
        scope=Settings.Scope.ORG,
        org=org,
        key="audit_retention_days",
        defaults={"value": 90},
    )
    Settings.objects.update_or_create(
        scope=Settings.Scope.GLOBAL,
        org=None,
        key="license_tier",
        defaults={"value": "pro"},
    )
    print(f"Seeded org {org.id} and team {team.id}")


if __name__ == "__main__":
    main()
