# Add SSRF Protection to Webhook Delivery System

## Overview

The deliver_webhook task in backend/api/tasks.py makes HTTP POST requests to user-controlled URLs (endpoint.url) without validation against internal/private IP ranges. An attacker could configure a webhook endpoint pointing to internal services like Redis, PostgreSQL, cloud metadata endpoints (169.254.169.254), or other internal network resources.

## Rationale

Server-Side Request Forgery (SSRF) is a critical vulnerability that could allow attackers to access internal infrastructure, bypass firewalls, read cloud metadata (AWS credentials, etc.), and potentially achieve remote code execution through internal services. The webhook system accepts arbitrary URLs from users, creating a significant attack surface.

---
*This spec was created from ideation and is pending detailed specification.*
