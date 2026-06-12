# Putcafe — feature backlog

A bag of feature ideas captured via `/feature`. Unsorted, unplanned — a holding
pen so nothing gets lost. Promote items into real PRDs when they're picked up;
check them off (`[x]`) or remove them once shipped.

## Backlog

- [ ] Separate prod/staging API + database  <!-- 2026-06-12 -->
      Today prod (`/web/`) and staging (`/web/staging/`) frontends hit the **same**
      API stack and **same** Postgres, so sessions/trades created in one env appear
      in the other. Fine for single-user MVP. Real isolation = a per-env compose
      stack + DB (or per-env schema/database in one Postgres) and env-scoped API
      routing (e.g. `/api/staging/*`). Decide when multi-env or multi-user matters.
- [ ] Rename positions-backend → session-backend  <!-- 2026-06-12 -->
      It owns sessions, positions, trades, balances — "session" is the truer name.
