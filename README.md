# NottMyTradeBinder

Self-hosted inventory manager for Pokémon and Weiss Schwarz cards across TCGPlayer and eBay.

When a card sells on either platform, inventory is automatically decremented and the other platform's listing quantity is updated.

## Features

- **Bulk listing** — Browse cards by game → set → card with full card images
- **Dual-platform** — List on TCGPlayer and eBay with separate prices per platform
- **Auto-sync** — Sales on either platform update the other automatically (5-minute polling + eBay webhooks)
- **Sales history** — Track all orders across both platforms in one place

## Setup

### 1. Get API credentials

**TCGPlayer**
- Apply at [developer.tcgplayer.com](https://developer.tcgplayer.com/)
- You need: `PUBLIC_KEY`, `PRIVATE_KEY`, `STORE_KEY` (your seller key)

**eBay**
- Apply at [developer.ebay.com](https://developer.ebay.com/)
- Create an app and get: `CLIENT_ID`, `CLIENT_SECRET`, `RuName` (redirect URI)
- Configure business policies (fulfillment, payment, return) in your eBay seller account

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your API credentials and server URL
```

Key settings:
```
APP_BASE_URL=https://your-server.com   # Public URL for eBay OAuth callback
EBAY_SANDBOX=false                      # Set to true for testing
SYNC_INTERVAL_MINUTES=5                # How often to poll for new orders
```

### 3. Deploy

```bash
docker compose up -d
```

The app will be available at `http://your-server` (port 80).

### 4. Connect eBay

Visit `http://your-server/settings` and click **Connect eBay Account** to complete OAuth.

### 5. (Optional) eBay Webhooks

For real-time sale notifications, configure an eBay Platform Notification subscription pointing to:
```
https://your-server.com/api/webhooks/ebay
```

Topic: `MARKETPLACE_ITEM_SOLD` or `ItemSold`

## Development

```bash
# Backend
cd backend
python -m venv .venv && .venv/bin/pip install -r requirements.txt
mkdir -p data
cp ../.env.example .env  # fill in values
PYTHONPATH=. .venv/bin/uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev   # proxies /api to localhost:8000
```

## Architecture

- **Backend**: FastAPI + SQLAlchemy + APScheduler (Python 3.12+)
- **Database**: SQLite (single file, Docker volume)
- **Frontend**: React + TypeScript + Tailwind CSS
- **Card data**: [TCG Tracking API](https://tcgtracking.com/tcgapi/) (no auth, free)
- **Deployment**: Docker Compose with nginx
