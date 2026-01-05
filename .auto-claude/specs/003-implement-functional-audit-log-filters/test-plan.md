# Audit Log Filters - Manual Test Plan

## Overview
This document outlines the comprehensive manual testing plan for the audit log filter functionality.

## Test Environment Setup
- Frontend development server running
- Backend API accessible
- Test data available in database

---

## Test Cases

### 1. Empty States

#### 1.1 No Filters Applied (Initial State)
- [ ] Load admin audit page
- [ ] Verify Filter button shows without badge
- [ ] Verify no active filter badges displayed
- [ ] Verify audit logs display correctly (or empty state if no data)

#### 1.2 Filters Applied with No Results
- [ ] Apply filters that yield no results
- [ ] Verify empty state displays with appropriate message
- [ ] Verify filter badges still show
- [ ] Verify clearing filters restores normal view

---

### 2. Single Filter Tests

#### 2.1 Action Type Filter
- [ ] Click Filter button → popover opens
- [ ] Select "Create" action
- [ ] Click Apply
- [ ] Verify URL updates with `?action=CREATE`
- [ ] Verify only CREATE actions shown in results
- [ ] Verify Filter button shows badge with "1"
- [ ] Verify active filter badge shows "Action: CREATE"

#### 2.2 Resource Type Filter
- [ ] Open filter popover
- [ ] Select "User" resource type
- [ ] Click Apply
- [ ] Verify URL updates with `?resource_type=User`
- [ ] Verify only User resources shown
- [ ] Verify badge count and label correct

#### 2.3 Actor Filter
- [ ] Open filter popover
- [ ] Enter actor email/ID in text field
- [ ] Click Apply
- [ ] Verify URL updates with `?actor_id={value}`
- [ ] Verify results filtered by actor
- [ ] Verify badge displays correctly

#### 2.4 Start Date Filter
- [ ] Open filter popover
- [ ] Select start date
- [ ] Click Apply
- [ ] Verify URL updates with `?start_date={date}`
- [ ] Verify only logs from that date forward shown
- [ ] Verify badge shows "From: {formatted date}"

#### 2.5 End Date Filter
- [ ] Open filter popover
- [ ] Select end date
- [ ] Click Apply
- [ ] Verify URL updates with `?end_date={date}`
- [ ] Verify only logs up to that date shown
- [ ] Verify badge shows "To: {formatted date}"

---

### 3. Multiple Filter Combinations

#### 3.1 Two Filters
- [ ] Apply action filter (e.g., CREATE)
- [ ] Apply resource type filter (e.g., User)
- [ ] Verify URL has both params: `?action=CREATE&resource_type=User`
- [ ] Verify results match both criteria
- [ ] Verify badge count shows "2"
- [ ] Verify both filter badges display

#### 3.2 Three Filters
- [ ] Apply action, resource_type, and actor filters
- [ ] Verify URL has all three params
- [ ] Verify results match all criteria
- [ ] Verify badge count shows "3"
- [ ] Verify all filter badges display correctly

#### 3.3 Date Range Filters
- [ ] Apply both start_date and end_date
- [ ] Verify URL has both date params
- [ ] Verify results within date range
- [ ] Verify both date badges display

#### 3.4 All Filters Combined
- [ ] Apply all five filter types
- [ ] Verify URL has all params
- [ ] Verify results match all criteria
- [ ] Verify badge count shows "5"
- [ ] Verify all filter badges display

---

### 4. Clearing Filters

#### 4.1 Clear Individual Filter (via Badge)
- [ ] Apply multiple filters
- [ ] Click X on one filter badge
- [ ] Verify that filter removed from URL
- [ ] Verify other filters remain
- [ ] Verify badge count decremented
- [ ] Verify results update correctly

#### 4.2 Clear All Filters (via "Clear all" button)
- [ ] Apply multiple filters
- [ ] Click "Clear all" button below filter badges
- [ ] Verify all filters removed from URL
- [ ] Verify no filter badges shown
- [ ] Verify Filter button badge disappears
- [ ] Verify results show unfiltered data

#### 4.3 Clear Filters (via Popover "Clear" button)
- [ ] Apply multiple filters
- [ ] Open filter popover
- [ ] Click "Clear" button in popover
- [ ] Verify all filters cleared
- [ ] Verify URL updated to remove all params
- [ ] Verify popover shows empty filter fields

---

### 5. Draft vs Applied Filter States

#### 5.1 Modify Without Applying
- [ ] Open filter popover
- [ ] Select a filter option
- [ ] Close popover WITHOUT clicking Apply
- [ ] Verify filter NOT applied to results
- [ ] Verify URL unchanged
- [ ] Verify no new badges appear

#### 5.2 Modify Then Apply
- [ ] Open filter popover
- [ ] Change multiple filters
- [ ] Click Apply
- [ ] Verify all changes applied together
- [ ] Verify URL updated with all changes
- [ ] Verify results reflect all filters

---

### 6. URL Synchronization & Shareability

#### 6.1 Direct URL Access
- [ ] Copy a filtered URL (e.g., `?action=CREATE&resource_type=User`)
- [ ] Paste into new browser tab
- [ ] Verify filters applied on page load
- [ ] Verify filter badges display
- [ ] Verify results match filters
- [ ] Open popover - verify form shows applied filters

#### 6.2 Browser Back/Forward
- [ ] Apply filter → navigate away → press back
- [ ] Verify filters restored
- [ ] Apply multiple filters in sequence
- [ ] Use browser back button
- [ ] Verify previous filter state restored

---

### 7. Export Functionality

#### 7.1 Export with No Filters
- [ ] Clear all filters
- [ ] Click Export button
- [ ] Verify export URL has no filter params
- [ ] Verify export downloads/opens correctly

#### 7.2 Export with Filters
- [ ] Apply multiple filters
- [ ] Click Export button
- [ ] Verify export URL includes all active filter params
- [ ] Verify exported data matches filtered results

---

### 8. Both Pages (Admin & Org)

#### 8.1 Admin Audit Page
- [ ] Test all above scenarios on `/admin/audit`
- [ ] Verify all functionality works correctly

#### 8.2 Org Audit Page
- [ ] Test all above scenarios on `/org/audit`
- [ ] Verify all functionality works correctly
- [ ] Verify shared components work identically

---

### 9. Edge Cases

#### 9.1 Invalid URL Parameters
- [ ] Manually enter invalid filter in URL
- [ ] Verify app handles gracefully (doesn't crash)

#### 9.2 Very Long Actor Search
- [ ] Enter very long string in actor field
- [ ] Verify UI handles appropriately

#### 9.3 Invalid Date Range
- [ ] Set end_date before start_date
- [ ] Verify results handle appropriately

#### 9.4 Rapid Filter Changes
- [ ] Quickly apply/clear filters multiple times
- [ ] Verify no race conditions or errors
- [ ] Verify final state is correct

---

## Success Criteria

All test cases must pass:
- ✅ Filter button opens popover with all filter options
- ✅ Each filter type works individually
- ✅ Multiple filters can be combined
- ✅ Filters can be cleared individually and all at once
- ✅ Active filter count displays correctly
- ✅ URL updates with filter state for shareability
- ✅ Export respects current filters
- ✅ Empty states display appropriately
- ✅ Draft and applied filter states work correctly
- ✅ Both admin and org pages function identically

---

## Test Results

_To be filled during manual testing_

### Test Session 1: [Date/Time]

**Tester:** Auto-Claude
**Environment:** Development
**Status:** In Progress

#### Results:
[To be documented during testing]

