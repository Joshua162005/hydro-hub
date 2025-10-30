# HydroHub — Cantilan Refill Station

A comprehensive Streamlit-based web application for water refill station management in Cantilan, Surigao del Sur, Philippines.

## Features

- **Secure Authentication**: Role-based access (Admin, Staff, Public)
- **Immutable Ledger**: Blockchain-style transaction tracking
- **Sales Management**: Record refill transactions with receipt uploads
- **Inventory Tracking**: Monitor gallons, filters, and supplies
- **Expense Management**: Track operational costs
- **Business Analytics**: Revenue, profit, and performance metrics
- **Data Export**: CSV/JSON reports with ledger verification

## Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Initialize Database**
   ```bash
   python -c "from hydrohub.db import init_db; init_db()"
   ```

4. **Run Application**
   ```bash
   streamlit run app.py
   ```

5. **Default Login**
   - Username: `admin`
   - Password: `admin123` (change immediately)

## Project Structure

```
hydrohub/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── .env                  # Environment configuration
├── hydrohub/             # Core application modules
│   ├── __init__.py
│   ├── db.py            # Database connection and setup
│   ├── models.py        # SQLAlchemy models
│   ├── auth.py          # Authentication system
│   ├── ledger.py        # Immutable ledger system
│   ├── ui_components.py # Reusable UI components
│   ├── reports.py       # Export and reporting
│   ├── validations.py   # Data validation
│   ├── storage.py       # File upload handling
│   └── utils.py         # Utility functions
├── migrations/          # Database migrations
├── data/               # Local data storage
│   └── receipts/       # Uploaded receipts
└── tests/              # Test suites
```

## Database Models

- **User**: Authentication and role management
- **RefillTransaction**: Water refill sales records
- **InventoryItem**: Stock tracking (gallons, filters, supplies)
- **Expense**: Operational cost tracking
- **Ledger**: Immutable transaction log

## Security Features

- Bcrypt password hashing
- Session management with timeout
- Role-based access control
- File upload validation
- Ledger integrity verification

## Business Metrics

- Daily/weekly/monthly P&L reports
- Inventory status and alerts
- Staff performance tracking
- Customer transaction history

## Deployment

### Local Development (SQLite)
Default configuration uses SQLite for easy setup.

### Production (PostgreSQL)
1. Set up PostgreSQL database
2. Update `DATABASE_URL` in `.env`
3. Run migrations: `alembic upgrade head`
4. Deploy using Docker or cloud platform

## Ledger System

The application maintains an immutable ledger for transparency:
- Every transaction is cryptographically linked
- Tampering detection through hash verification
- Audit trail for all business operations
- Export capabilities for external verification

## Support

For issues or questions, contact the development team or refer to the documentation in the `docs/` directory.

## License

Proprietary software for Cantilan water refill stations.
