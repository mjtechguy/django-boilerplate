# Add User API Keys Management to Profile Page

## Overview

Add a new 'API Keys' section to the user profile page allowing users to create, list, and revoke their own API keys using the existing backend endpoints.

## Rationale

Backend has complete API key management (UserAPIKeyListView, UserAPIKeyCreateView, UserAPIKeyRevokeView) at /api/v1/me/api-keys but the frontend profile page only has placeholder UI. The profile page already has Card sections for Security features making this a natural extension.

---
*This spec was created from ideation and is pending detailed specification.*
