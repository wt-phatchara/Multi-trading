# Production Deployment Guide

This guide covers production-level deployment with all enterprise features enabled.

---

## 🏗️ Production Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Load Balancer (Optional)              │
└───────────────────────┬─────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼───────┐ ┌─────▼──────┐ ┌─────▼──────┐
│ Trading Agent │ │ Trading    │ │  Trading   │
│  Instance 1   │ │ Instance 2 │ │ Instance 3 │
└───────┬───────┘ └─────┬──────┘ └─────┬──────┘
        │               │               │
        └───────────────┼───────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼───────┐ ┌─────▼──────┐ ┌─────▼──────┐
│  PostgreSQL   │ │   Redis    │ │ Prometheus │
│   (State)     │ │  (Cache)   │ │ (Metrics)  │
└───────────────┘ └────────────┘ └────────────┘
        │               │               │
        └───────────────▼───────────────┘
                    Grafana
```

---

## 📋 Prerequisites

### Required
- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum (8GB recommended)
- 20GB disk space
- PostgreSQL 15+ (or use Docker)
- Redis 7+ (or use Docker)

### Optional
- Kubernetes cluster (for scaled deployment)
- Prometheus + Grafana (monitoring)
- Sentry account (error tracking)

---

## 🚀 Quick Production Setup

### 1. Clone and Configure

```bash
git clone <repository>
cd Multi-trading

# Copy production environment template
cp .env.production .env

# Edit with your settings
nano .env
```

### 2. Set Master Password

```bash
# Generate strong password
export MASTER_PASSWORD=$(openssl rand -base64 32)

# Add to .env
echo "MASTER_PASSWORD=$MASTER_PASSWORD" >> .env
```

### 3. Configure Secrets

```bash
# Encrypt your API keys
python3 -c "
from src.core.secrets_manager import SecretsManager
import os

os.environ['MASTER_PASSWORD'] = 'your_master_password'
manager = SecretsManager()

secrets = {
    'exchange_api_key': 'your_binance_api_key',
    'exchange_api_secret': 'your_binance_api_secret',
    'sentry_dsn': 'your_sentry_dsn',  # optional
    'redis_password': 'your_redis_password',
    'db_password': 'your_db_password'
}

manager.encrypt_secrets(secrets)
print('✅ Secrets encrypted successfully!')
"
```

### 4. Deploy with Docker

```bash
# Deploy all services
chmod +x deploy-prod.sh
./deploy-prod.sh
```

---

## 🔐 Security Hardening

### API Keys Management

1. **Never commit API keys**
2. **Use encrypted secrets** (secrets.enc)
3. **Rotate keys regularly**
4. **Limit API permissions** (no withdrawal)
5. **Enable IP whitelisting** on exchange

### Rotating API Keys

```bash
python3 -c "
from src.core.secrets_manager import SecretsManager
import os

os.environ['MASTER_PASSWORD'] = 'your_master_password'
manager = SecretsManager()

manager.rotate_api_keys(
    new_api_key='new_key',
    new_api_secret='new_secret'
)
print('✅ API keys rotated')
"
```

### Database Security

```bash
# Use strong passwords
DB_PASSWORD=$(openssl rand -base64 32)

# Enable SSL connections
# Add to docker-compose.yml postgres service:
command: >
  -c ssl=on
  -c ssl_cert_file=/var/lib/postgresql/server.crt
  -c ssl_key_file=/var/lib/postgresql/server.key
```

---

## 📊 Monitoring & Observability

### Accessing Dashboards

- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9091
- **Agent Health**: http://localhost:8000/health

### Key Metrics to Monitor

1. **Trading Metrics**
   - Win rate
   - Daily P&L
   - Open positions
   - Trade frequency

2. **System Metrics**
   - CPU usage
   - Memory usage
   - API latency
   - Error rate

3. **Safety Metrics**
   - Drawdown
   - Circuit breaker status
   - Kill switch triggers
   - Position reconciliation

### Alerts Configuration

Edit `monitoring/prometheus.yml` to add alerts:

```yaml
- alert: HighDrawdown
  expr: trading_drawdown_percent > 8
  for: 1m
  annotations:
    summary: "High drawdown detected"

- alert: ExchangeAPIDown
  expr: up{job="trading_agent"} == 0
  for: 30s
  annotations:
    summary: "Trading agent is down"
```

---

## 🧪 Running Backtests

### Basic Backtest

```bash
python run_backtest.py \
  --exchange binance \
  --symbol BTC/USDT \
  --timeframe 5m \
  --days 30 \
  --capital 10000 \
  --strategy advanced
```

### Advanced Backtest with Custom Parameters

```bash
python run_backtest.py \
  --exchange binance \
  --symbol ETH/USDT \
  --timeframe 15m \
  --days 60 \
  --capital 50000 \
  --strategy advanced \
  --leverage 3 \
  --position-size 1.5 \
  --stop-loss 1.5 \
  --take-profit 3.0 \
  --min-confidence 0.7
```

### Analyzing Results

Backtest outputs:
- **Text report**: Comprehensive metrics
- **Equity curve CSV**: For plotting in Excel/Python
- **Trade log**: Detailed trade-by-trade analysis

---

## 🔄 Database Operations

### Backups

```bash
# Backup database
docker-compose exec postgres pg_dump -U trading_user trading_db > backup_$(date +%Y%m%d).sql

# Restore database
docker-compose exec -T postgres psql -U trading_user trading_db < backup_20240315.sql
```

### Migrations

```bash
# Create migration
docker-compose exec trading_agent alembic revision -m "add new table"

# Run migrations
docker-compose exec trading_agent alembic upgrade head

# Rollback
docker-compose exec trading_agent alembic downgrade -1
```

---

## 🛡️ Kill Switch Management

### Manual Trigger

```bash
# Via HTTP API
curl -X POST http://localhost:8000/api/kill-switch/trigger \
  -H "Content-Type: application/json" \
  -d '{"reason": "Manual intervention needed"}'
```

### Reset Kill Switch

```bash
curl -X POST http://localhost:8000/api/kill-switch/reset \
  -H "Content-Type: application/json" \
  -d '{"manual_override": true}'
```

### Check Status

```bash
curl http://localhost:8000/api/kill-switch/status
```

---

## 🧪 Testing

### Run Unit Tests

```bash
# Install test dependencies
pip install -r requirements-prod.txt

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test
pytest tests/test_backtest.py::test_backtest_run -v
```

### Integration Tests

```bash
# Test with paper trading
TRADING_MODE=paper python main.py --test-mode

# Test database connection
python -c "from src.core.database import DatabaseManager; db = DatabaseManager('postgresql://user:pass@localhost/db'); db.create_tables(); print('✅ DB OK')"
```

---

## 🔍 Troubleshooting

### Agent Won't Start

```bash
# Check logs
docker-compose logs trading_agent

# Check health
docker-compose exec trading_agent python -c "from src.core.resilience import HealthCheck; hc = HealthCheck(); print(hc.get_status())"
```

### Database Connection Issues

```bash
# Test connection
docker-compose exec postgres psql -U trading_user -d trading_db -c "SELECT 1"

# Check logs
docker-compose logs postgres
```

### Position Reconciliation Failed

```bash
# Force reconciliation
curl -X POST http://localhost:8000/api/reconcile-positions
```

---

## 📈 Performance Optimization

### Database

```sql
-- Add indexes
CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_trades_entry_time ON trades(entry_time);
CREATE INDEX idx_market_data_symbol_timestamp ON market_data(symbol, timestamp);
```

### Redis Caching

```python
# Enable caching in config
ENABLE_REDIS_CACHE=true
REDIS_TTL=300  # 5 minutes
```

### Connection Pooling

```bash
# Optimize in .env
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
REDIS_POOL_SIZE=20
```

---

## 🚨 Incident Response

### If Trading Goes Wrong

1. **Immediate Actions**
   ```bash
   # Trigger kill switch
   curl -X POST http://localhost:8000/api/kill-switch/trigger

   # Close all positions manually on exchange
   ```

2. **Investigation**
   ```bash
   # Check logs
   docker-compose logs trading_agent | grep ERROR

   # Check database
   docker-compose exec postgres psql -U trading_user -d trading_db -c "SELECT * FROM trades ORDER BY created_at DESC LIMIT 10"
   ```

3. **Recovery**
   ```bash
   # Fix issue
   # Reset kill switch
   curl -X POST http://localhost:8000/api/kill-switch/reset

   # Restart agent
   docker-compose restart trading_agent
   ```

---

## 📝 Maintenance

### Daily Tasks
- ✅ Check Grafana dashboards
- ✅ Review error logs
- ✅ Verify position reconciliation
- ✅ Check daily P&L

### Weekly Tasks
- ✅ Database backup
- ✅ Review backtest performance
- ✅ Update strategy parameters if needed
- ✅ Check disk space

### Monthly Tasks
- ✅ Rotate API keys
- ✅ Review and optimize strategies
- ✅ Update dependencies
- ✅ Security audit

---

## 🔗 Related Documentation

- [Beginner's Guide](BEGINNER_GUIDE.md) - For non-technical users
- [Quick Start](QUICK_START.md) - Fast setup guide
- [README](README.md) - Project overview
- [API Documentation](API_DOCS.md) - REST API reference

---

## ⚠️ Production Checklist

Before going live:

- [ ] Test with paper trading for 2+ weeks
- [ ] Test with testnet environment
- [ ] Backtest strategy on 3+ months of data
- [ ] Set up monitoring and alerts
- [ ] Configure kill switch properly
- [ ] Enable database backups
- [ ] Set conservative risk limits
- [ ] Test fail-over scenarios
- [ ] Document incident response plan
- [ ] Enable audit logging
- [ ] Verify API key permissions (no withdrawal)
- [ ] Set up Sentry for error tracking
- [ ] Test position reconciliation
- [ ] Review all logs for warnings
- [ ] Start with small capital

---

**Remember: This is production-grade software handling real money. Always prioritize safety over profits!**
