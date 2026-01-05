# Create Reusable Header Component to Reduce Layout Duplication

## Overview

The AdminHeader and OrgHeader components share approximately 70% identical code structure including search input, theme toggle, and notification dropdown patterns. Only minor differences exist (placeholder text, notification content, org indicator).

## Rationale

Duplicated component structures require updating multiple files for common changes like styling updates or feature additions. A shared base component would improve maintainability.

---
*This spec was created from ideation and is pending detailed specification.*
