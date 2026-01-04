# Add Search and Filters to Organizations Admin List

## Overview

Add text search input and status/license tier filter dropdowns to the Organizations admin list page, matching the filter pattern already used in the Users admin list.

## Rationale

Backend API in views_admin_orgs.py already supports search, status, and license_tier query parameters. Frontend useOrganizations hook already accepts params. The Users page demonstrates the exact filter UI pattern with Select components. Organizations page has no filtering despite backend support.

---
*This spec was created from ideation and is pending detailed specification.*
