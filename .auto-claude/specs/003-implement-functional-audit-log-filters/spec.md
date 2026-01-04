# Implement Functional Audit Log Filters

## Overview

Wire up the non-functional Filter button in the Audit Logs page to show a filter popover allowing filtering by action type, resource type, actor, and date range.

## Rationale

The Audit Logs page has a Filter button in the UI but it does nothing when clicked. Backend views_audit.py already supports action, resource_type, actor_id, start_date, end_date filters via query params. Only the filter UI and state management are missing.

---
*This spec was created from ideation and is pending detailed specification.*
