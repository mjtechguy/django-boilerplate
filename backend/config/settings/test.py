from .base import *  # noqa: F401,F403

# Test signing key for audit log integrity tests
AUDIT_SIGNING_KEY = "test-signing-key-for-audit-logs"

# Test encryption keys for field encryption tests
FIELD_ENCRYPTION_KEYS = ["test-encryption-key-32-bytes-lon"]  # 32 chars for Fernet

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "idempotency": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "cerbos": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
}

# Use in-memory channel layer for testing (no Redis required)
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
}

DEBUG = True

# Test RSA keys for local JWT authentication
# These are only used in tests - NOT for production
LOCAL_AUTH_PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
MIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQC2+hL4ok24lLyF
DFt7eP0kjAp2cykOw6zdOHdaS0JJHKcXa/MR6LJJchtoQDFT51fM92lr96N9iaFq
5s+L+LbNBV1GEbkwKClfHjyrrdIEVLcDibpXdg8qGRHhMiJQxgTsM4aIH7+NVF87
1yMJjIVtnCdqv0RTT1/gbcAwt0hKDsIJbJR4j9SFV7YDwQxvdi4lKSKAQMIjr1Gc
hhczDfdJTy50FO7p/L90gzv0A3OL/Tv/JqTkQAxZNvoS4Ns0uRlHqKmURjBjKnHc
sjEynxew4Jjj4S4OyPegztfgc1Y++YfVExz+rm8jtCkZegHR1rA+nv3lByWVlKbe
r6IjwRApAgMBAAECggEAFZejovsWNFy69XFsn0C7ELPE7U7wLqmZLd7iuMFOUG3k
6u7md3vQBDpGsTH4EDhp5EpjAqZtwNv7tC+KGPCv87g5FlJzmdL3dN3O14ySzseH
dE+tsXIBXpyoPzypD4KapJv8+XXTpzQoa9marR8LxNBLV328LJ+ehw+0gRsz2Oc6
zu9y1eRz3SsSUpg/Q9H2pBtVbB3CtyEgYMriJpUVcoJSceFzUv9tjDcV1m3Ne1Q/
64GabjcfcqqMRqLih+lUoHq+q2O8WpQJFCqIfflIgxuBxJ52BoPtexiT3CnUdadH
hEiM59NcI2KJsDuUn2id0iHXayslXE0V+8rxPXREQQKBgQD6bw60XEBLW3Ti2xGP
2SmW+g9Rpi7Xdu2u/zKj4QrxEmN7EFoXIxiTG/gahcxI+oWVRteQEJ2NVzwu8oWw
LmfsuQoyBMrrN3Dg43r+7QCa8LbaKMVa22lnHW56g3SQg5KN8YStSxSFBprl6TYx
nIWDV7I8ezLsNUTNUwMKafaJSQKBgQC7CzGI+cjNtHOlGcmVbXxMr/JqZUPD3eSM
h7futTwMl4CgbIN3HQ4LmoTbJ7zGnQdctnRW4PkTjvW0vDwc+LNJPvjtz80bI0mg
uSTFIrIszBQ7q0DxmNkW0GsqYxJD5CzzmPWmO33Hf2371lO5M/XVACjTOMUrkPkf
TZgvNe4v4QKBgE6QqLxMdJ8vgevpbgkCx9lleYjT6b4OwWI1DV38K8KVUkA5UQoR
KJR+IcewUfZTIbVDFD1N+R9uTqMr0mUDKfdJ1bj7Z+2C5xamRt/S2m3BNpwaTk/C
pb6DrTUiKF9t53xAWK9E7psNB2s5Tpch04Dw8imnPMJ9s6f2cu3BcGaBAoGAYgM9
k8+AX/qdVviqX3kd13mjiAlEd1DBQLqlsZqauuZw6p+yTCqXf5Ea6VRrYZBLmVOq
pxQAsTUKoAi7X1sbZ9htzQBFNGFLZcNe90Z1I3BVcecNgwxbRc81OOLtYVIiFAwl
PVSTVoT59yuad8Q4n8MToYtwFqJDSRn6E1MpW0ECgYBh5bZno/JPpKGk4CDahyCp
hBsF5PkqzTkie1BhSKzMKDfglrLeYmcIH/bJzrvsfe1Jjhpo+EaBlqA6t/bquMtN
m8SRu+Ep2xUtAd6TLoV8x/CATA82k/6D2aJ4U68boJnjusb4x7E4ywSCFaKj5+2M
55mB6g1/1fpmOsmBo+VUOA==
-----END PRIVATE KEY-----"""

LOCAL_AUTH_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAtvoS+KJNuJS8hQxbe3j9
JIwKdnMpDsOs3Th3WktCSRynF2vzEeiySXIbaEAxU+dXzPdpa/ejfYmhaubPi/i2
zQVdRhG5MCgpXx48q63SBFS3A4m6V3YPKhkR4TIiUMYE7DOGiB+/jVRfO9cjCYyF
bZwnar9EU09f4G3AMLdISg7CCWyUeI/UhVe2A8EMb3YuJSkigEDCI69RnIYXMw33
SU8udBTu6fy/dIM79ANzi/07/yak5EAMWTb6EuDbNLkZR6iplEYwYypx3LIxMp8X
sOCY4+EuDsj3oM7X4HNWPvmH1RMc/q5vI7QpGXoB0dawPp795QcllZSm3q+iI8EQ
KQIDAQAB
-----END PUBLIC KEY-----"""

# Celery test settings
CELERY_TASK_ALWAYS_EAGER = True  # Execute tasks synchronously in tests
CELERY_TASK_EAGER_PROPAGATES = True  # Propagate exceptions in eager mode

# Django-Axes test settings
AXES_ENABLED = False  # Disable axes in tests to avoid lockouts

# Disable rate limiting in tests
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []  # noqa: F405
