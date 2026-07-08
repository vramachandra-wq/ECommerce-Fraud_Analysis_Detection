# Fraud Analysis and Detection — Streamlit POC

A app with three portals (Customer, Fraud Analyst, Admin)
backed by PostgreSQL via psycopg2, evaluating orders against a 10-rule
fraud engine.

```

## Architecture

```
app.py                    # Navigation shell (sidebar portal switcher)
config.py                 # Env-based DB config
database/
  connection.py           # ThreadedConnectionPool, cached via st.cache_resource
  schema.sql              # Original schema, verbatim, + one addendum (see below)
auth/
  customer_auth.py        # master.customers login
  analyst_auth.py         # master.analyst_users login + role check
fraud_engine/
  rules.py                # R001–R010 individual checks (R011 excluded, see below)
  engine.py                # Runs all rules, resolves conflicts, builds disposition
  auto_approval.py        # Lazy sweep for expired R001 holds
portals/
  customer_portal.py      # Login -> order form -> submit -> ID-only confirmation
  analyst_dashboard.py    # Queue + review UI (also reused by Admin overrides)
  admin_panel.py           # User mgmt, analytics, rule stats, override tab
utils/
  order_utils.py           # Order ID generation, pricing
  queries.py                # Shared read queries (dashboards, queue, stats)
```

## Recent additions (IP Blacklist mgmt, RBAC, Analytics)

- **IP Blacklist** (`master.ip_blacklist`) is now history-preserving: every
  blacklist/whitelist action inserts or updates a row, but only one *active*
  row per IP is allowed at a time (`ux_ip_blacklist_active_ip` partial unique
  index). Analysts can blacklist an IP inline from Order Review (Fraud
  Dashboard or Admin override tab) with a mandatory reason, or manage any IP
  from Admin Panel → **IP Blacklist** (check status, blacklist, or whitelist).
  R007 only matches `is_active = TRUE` rows.
- **Page-level RBAC** (`master.analyst_permissions`): Admins always have full
  access to both existing pages (Fraud Analyst Dashboard, Admin Control
  Panel). Non-admin analysts only see pages an Admin has explicitly granted
  them via Admin Panel → **Analyst Permissions**; the sidebar and the render
  dispatch both re-check the grant, so a restricted page can't be reached
  even by forcing session state.
- **Admin Analytics** gained an **Orders Over Time** line chart: current
  month, grouped by day, re-queried on every render so new orders show up
  automatically.

## Key decisions made while building (per your answers)

1. **180-minute R001 auto-approval** is implemented as a *lazy sweep*:
   `fraud_engine/auto_approval.sync_expired_holds()` runs at the top of the
   Analyst Dashboard and Admin Panel on every page load/rerun. It
   auto-approves any `ON_HOLD` order whose window has elapsed and that
   hasn't been manually rejected. There is no persistent background
   worker — if nobody opens either dashboard, the sweep simply runs the
   next time someone does, and back-dates nothing incorrectly since it's
   driven by `order_timestamp + delay_minutes`, not wall-clock polling.

2. **R011 (Location Velocity) is not implemented.** The schema has no
   location/city field anywhere — `orders.address` is free text — so
   there's no reliable signal to evaluate "multiple locations" against.
   It's still seeded in `master.rule_master` for reference and shows up
   in the Admin rule-stats table with a trigger count of 0. If you later
   add a normalized location column (or derive one from IP geolocation),
   the check can be dropped into `fraud_engine/rules.py` alongside R001–R010.

3. **Conflicting rules resolve by strictest action**: if an order trips
   both a `REVIEW` rule and a `REJECTED` rule, the final `order_status`
   is `REJECTED` (`REJECTED` > `ON_HOLD` > `PENDING_REVIEW`), and every
   triggered rule's reason is concatenated into `flagged_reason`.
   `delay_minutes` is only set to 180 when R001 triggers *and* it's the
   rule that ultimately determines the outcome (i.e. nothing stricter
   overrides it) — if R007 (blacklisted IP) also fires, the order is
   rejected outright and there's no hold window to honor.

## Other assumptions worth knowing about

- **R007 (blacklisted IP) is an immediate, automatic rejection** at
  order-submission time — it does *not* go through the analyst queue.
  This matches the spec's "Queue: View pending/on-hold orders" (i.e. the
  queue only ever shows `ON_HOLD` / `PENDING_REVIEW`, not `REJECTED`).
- **Program track, device, and IP address are all manual/editable fields**
  on the order form, separate from the customer's stored profile — the
  spec explicitly calls out IP as "for demo purposes," and program/device
  need to be adjustable too so you can actually trigger R001/R004/R010 in
  a demo without seeding a second customer.
- **Passwords are compared in plaintext**, matching the schema's
  `VARCHAR` password columns and plaintext seed data. This is fine for a
  POC; swap in bcrypt + a hashed column before this touches anything real.
- **Order IDs** are generated as `ORD000001`, `ORD000002`, ... via a
  Postgres sequence (`master.order_id_seq`), added in an addendum at the
  bottom of `schema.sql` — no existing table, column, or relationship
  was altered.
- **Rule-trigger stats** (Admin → Rule Stats tab) are derived by pattern-
  matching `flagged_reason LIKE '%R00X:%'`, since the schema doesn't have
  a normalized rule-trigger log table. Good enough for a POC dashboard;
  a proper `order_rule_triggers` join table would be more robust if this
  becomes a real product.