# Add Rate Limiting and Quotas for API Key Creation

## Overview

The UserAPIKeyCreateView in backend/api/views_api_keys.py allows authenticated users to create unlimited API keys without rate limiting or per-user quotas. An attacker with valid credentials could create thousands of API keys, potentially exhausting database resources and complicating security audits and key revocation.

## Rationale

Unbounded resource creation can lead to denial of service through resource exhaustion. Additionally, having unlimited API keys per user makes it difficult to identify compromised keys, increases the attack surface, and creates management overhead. Most SaaS applications limit API keys to a reasonable number (e.g., 10-50 per user).

---
*This spec was created from ideation and is pending detailed specification.*
