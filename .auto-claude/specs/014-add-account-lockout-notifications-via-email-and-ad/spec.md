# Add Account Lockout Notifications via Email and Admin Alerting

## Overview

While django-axes is properly configured for brute force protection (AXES_FAILURE_LIMIT=5, AXES_COOLOFF_TIME=1 hour), there is no notification mechanism to alert users when their account is locked due to failed login attempts. Users remain unaware that their account may be under attack.

## Rationale

Account lockout notifications serve two purposes: (1) They alert legitimate users that their account may be compromised, prompting password changes and investigation, and (2) They provide transparency about security events. Without notifications, attackers can probe accounts undetected. Additionally, mass lockout events indicate credential stuffing attacks requiring immediate response.

---
*This spec was created from ideation and is pending detailed specification.*
