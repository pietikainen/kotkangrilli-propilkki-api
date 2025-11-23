# Propilkki Tournament Backend API

FastAPI backend for Pro Pilkki 2 ice fishing tournament statistics.

## 🚀 Quick Start (Local Development)

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your DATABASE_URL

# Run
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

## 🐳 Docker

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## 📡 API Endpoints

### Statistics
- `GET /api/stats/leaderboard?limit=10&lake=Särkijärvi` - Top players
- `GET /api/stats/species?lake=Särkijärvi` - Species statistics
- `GET /api/stats/lakes` - Lake statistics
- `GET /api/stats/recent?limit=20&player=PlayerName` - Recent catches

### Health
- `GET /health` - Health check
- `GET /` - API info

## 🗄️ Database

Connects to existing PostgreSQL database on localhost:
- Host: `localhost` (container uses `--network host`)
- Database: `pp2stats`
- Table: `competition_catches`
- Port 5432 is firewalled (ufw deny) - only localhost connections allowed

## 🔧 Environment Variables

```
DATABASE_URL=postgresql://user:pass@host:5432/pp2stats
CORS_ORIGINS=http://localhost:3000,http://your-server-ip
```
