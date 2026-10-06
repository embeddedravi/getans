# Admin Approval Controls — Implementation Plan

## Overview
Add admin approval workflows for **Publishers**, **Advertisers**, and **Ad Slots (Ad Units)** so that newly created/self-registered entities start in a "pending" state and must be explicitly approved or rejected by an admin before becoming active.

## Current State Analysis

| Entity | Current Status System | Approval Gap |
|---|---|---|
| **Publisher** | Has `PublisherStatus` enum: `pending_approval`, `active`, `suspended`, `rejected` ✅ | No API endpoint to change status (approve/reject) |
| **Advertiser** | Has `AccountStatus` enum: `pending_verification`, `active`, `suspended`, `archived` | No `rejected` status; no approval endpoint |
| **Ad Unit** | Only has `is_active` boolean | No approval status at all |
| **Creative** | Has `ReviewStatus` + `/review` endpoint ✅ | Already fully implemented (reference pattern) |

## Changes

### 1. Backend — Models

#### `advertiser.py`
- Add `REJECTED = "rejected"` to `AccountStatus` enum

#### `ad_unit.py`
- Add `AdUnitStatus` enum: `pending_review`, `approved`, `rejected`
- Add `status` column with default `pending_review`
- Add `rejection_reason` column (optional)

---

### 2. Backend — Schemas

#### `schemas/advertiser.py`
- Add `REJECTED = "rejected"` to schema `AccountStatus`
- Add `AdvertiserReview` schema (status + optional rejection_reason)
- Add `rejection_reason` field to `AdvertiserOut`

#### `schemas/publisher.py`
- Add `PublisherReview` schema (status + optional rejection_reason)
- Add `rejection_reason` field to `PublisherOut`

#### `schemas/add_unit.py`
- Add `AdUnitStatus` enum: `pending_review`, `approved`, `rejected`
- Add `AdUnitReview` schema
- Add `status` and `rejection_reason` to `AdUnitOut`

---

### 3. Backend — Models (Publisher)

#### `publisher.py`
- Add `rejection_reason` column (optional String)

---

### 4. Backend — Models (Advertiser)

#### `advertiser.py`
- Add `rejection_reason` column (optional String)

---

### 5. Backend — API Endpoints

#### New file: `api/admin.py` — Admin Approval Router
All endpoints admin-only (`require_role("admin")`):

| Method | Path | Description |
|---|---|---|
| `GET` | `/admin/approvals/pending` | List all pending publishers, advertisers, and ad units |
| `PATCH` | `/admin/publishers/{id}/review` | Approve/reject a publisher |
| `PATCH` | `/admin/advertisers/{id}/review` | Approve/reject an advertiser |
| `PATCH` | `/admin/ad-units/{id}/review` | Approve/reject an ad unit |

#### Wire into `main.py`
- Import and register the new `admin.router`

---

### 6. Backend — Alembic Migration
- Generate migration for the new columns and enum values

---

### 7. Flask Dashboard

#### `app.py`
- Add routes for the new admin approvals page
- Add proxy routes for approve/reject actions
- Add "Approvals" to the sidebar navigation

#### New template: `templates/approvals.html`
- Tabbed UI showing pending Publishers, Advertisers, and Ad Units
- Each item shows details + Approve/Reject buttons
- Rejection requires a reason (modal)

#### `templates/layout.html`
- Add "Approvals" nav link (admin-only, shown with badge count)

#### `templates/publishers.html`
- Show rejection_reason if publisher is rejected
- Show approve/reject buttons for admin when status is pending

---

### 8. React Dashboard

#### `lib/api.ts`
- Add API calls: `listPendingApprovals`, `reviewPublisher`, `reviewAdvertiser`, `reviewAdUnit`

#### `types.ts`
- Add `AdUnitStatus` type, update `AdUnit` interface
- Add `AccountStatus` / `AdvertiserStatus` type
- Add `Advertiser` interface

#### New page: `pages/ApprovalsPage.tsx`
- Tabbed view of pending items with approve/reject actions

#### `components/Sidebar.tsx`
- Add "Approvals" link (for admin role)

#### `App.tsx`
- Add route for `/approvals`

---

## Execution Order
1. Models (add columns/enums)
2. Schemas (add new Pydantic models)
3. API endpoints (`admin.py`)
4. Wire into `main.py`
5. Alembic migration
6. Flask dashboard (routes + template + sidebar)
7. React dashboard (api + types + page + sidebar + routing)
