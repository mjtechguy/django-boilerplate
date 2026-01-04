# Connect Notifications Page to Real WebSocket Events

## Overview

Replace the mock notification data in the Notifications page with real-time updates using the existing WebSocket infrastructure and orgEvents pattern.

## Rationale

WebSocket infrastructure exists in lib/websocket/ with ws-context.tsx managing connections and orgEvents. Notifications page has complete UI but uses hardcoded mock data. The orgEvents pattern already accumulates real-time events that should power the notifications UI.

---
*This spec was created from ideation and is pending detailed specification.*
