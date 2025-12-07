import django

django.setup()

from api.models import Org, SampleResource, Settings, Team  # noqa: E402


def main():
    org = Org.objects.create(name="Acme Health", license_tier="pro", feature_flags={"export": True})
    team = Team.objects.create(org=org, name="Care Team")
    SampleResource.objects.create(org=org, team=team, name="seed-resource")
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
