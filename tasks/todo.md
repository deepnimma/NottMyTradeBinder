# NottMyTradeBinder — Implementation Tracker

## Status Legend
- [x] Complete
- [~] In Progress
- [ ] Pending

---

## Phase 1: Foundation [x]
- [x] FastAPI app skeleton (`backend/app/main.py`)
- [x] Pydantic config from .env (`config.py`)
- [x] SQLAlchemy + SQLite (`database.py`)
- [x] DB models: Card, InventoryItem, Order
- [x] Pydantic schemas for all models
- [x] Base routers: cards, inventory, orders, settings, webhooks
- [x] `backend/Dockerfile`
- [x] `.env.example`
- [x] Verified: DB creates OK, FastAPI loads all routes, Python 3.14 compat fix (SQLAlchemy 2.0.47)

## Phase 2: Card Data Layer [x]
- [x] `card_data/tcgtracking.py` — TCGTracking API client (base: tcgtracking.com/tcgapi/v1)
- [x] Discovered: Pokemon=cat3, Weiss Schwarz=cat20; response shapes verified live
- [x] `card_data/sync.py` — upsert cards to DB, card_number fallback = `tcg-{product_id}`
- [x] `/api/cards/sets?game=` — serves from live API
- [x] `/api/cards/by-set?set_id=&game=` — DB-cached, auto-fetches on cache miss
- [x] `/api/cards/sync-set` — force sync a set
- [x] `/api/cards/search` — full-text search on cached cards
- [x] Verified: 288 Pokémon cards synced, 166 WS sets loaded

## Phase 3: TCGPlayer Integration [x]
- [x] `integrations/tcgplayer.py` — auth, create/update SKU, update quantity, delist, get orders
- [x] `routers/tcgplayer.py` — list/delist/orders-sync endpoints

## Phase 4: eBay Integration [x]
- [x] `integrations/ebay.py` — OAuth flow, create/replace inventory item, create/publish offer, update quantity, delist, get orders
- [x] `routers/ebay.py` — auth-url, callback, status, list/delist/orders-sync endpoints
- Note: eBay listing policy IDs (fulfillment, payment, return) must be set in ebay.py create_offer() after user configures them in eBay seller account

## Phase 5: Sync Engine + Scheduler [x]
- [x] `sync/engine.py` — on_sale(platform, order_data) → decrement qty → update other platform (delist if qty=0)
- [x] `sync/scheduler.py` — APScheduler polling every 5 min for both platforms
- [x] eBay webhook receiver wired to engine (background task)

## Phase 6: React Frontend [x]
- [x] Scaffolded React + TypeScript + Tailwind with Vite
- [x] Dashboard page (stats + recent sales + manual sync buttons)
- [x] AddInventory page (Game→Set→Card cascading dropdowns, per-platform prices)
- [x] InventoryList page (table, inline edit, list/delist per platform)
- [x] SalesHistory page (all orders with revenue summary)
- [x] Settings page (masked API key display, eBay OAuth connect button)
- [x] Verified: `npm run build` succeeds cleanly

## Phase 7: Docker + Deployment [x]
- [x] `frontend/Dockerfile` multi-stage build + nginx config
- [x] `docker-compose.yml` (backend + frontend, shared SQLite volume)
- [x] `README.md` full setup instructions
- [x] `.env.example` with all keys documented

---

## Notes / Decisions
- SQLAlchemy 2.0.47 required for Python 3.14 compatibility (2.0.36 fails)
- TCGTracking API base URL: `https://tcgtracking.com/tcgapi/v1` (not `/tcgapi/`)
- Card number fallback: `tcg-{product_id}` for non-card products with null number field
- Prices per-platform: separate `tcgplayer_price` and `ebay_price` columns
- eBay condition mapping: NM → LIKE_NEW, LP → VERY_GOOD, MP → GOOD, HP → ACCEPTABLE
- eBay listing policies (fulfillment/payment/return IDs) must be configured by user in Settings
