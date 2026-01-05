# Extract Duplicated Sidebar Context into Shared Generic Component

## Overview

The sidebar context implementation is duplicated across admin-layout and org-layout. Both files define identical SidebarContextType interface and nearly identical provider components, differing only in storage key and naming.

## Rationale

Code duplication increases maintenance burden. Fixing bugs or adding features requires changes in multiple places, increasing the risk of inconsistency.

---
*This spec was created from ideation and is pending detailed specification.*
