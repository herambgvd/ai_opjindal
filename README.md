# AI OpJindal - Video Analytics Platform

A comprehensive Django-based video analytics platform with real-time cross-counting capabilities, TimescaleDB optimization, and advanced data analysis features.

## 🚀 Features

### Core Functionality
- **Region & Camera Management**: Complete CRUD operations for managing regions and cameras
- **Bulk CSV Upload**: Upload CSV files to create multiple cameras at once via Django admin
- **Real-time MQTT Data Processing**: Continuous data ingestion from camera endpoints
- **TimescaleDB Integration**: Optimized time-series database for high-frequency data storage
- **Advanced Analytics**: Three comprehensive analysis views with interactive charts
- **CSV Export**: Export analysis data in structured CSV format
- **Public Display**: TV-friendly occupancy display for guest viewing
- **Enhanced Dashboard**: Real-time platform statistics and system health monitoring

### Analysis Views
1. **Daily Analysis**: Analyze region data for a specific date with hourly trends
2. **Comparative Analysis**: Compare data between two dates with visual comparisons
3. **Comprehensive Analysis**: Analyze data over date ranges (up to one week) with daily trends

### Data Visualization
- Interactive charts using ApexCharts library
- Real-time occupancy percentage displays
- Responsive design for desktop and mobile viewing
- TV-optimized public display interface

## 🛠 Technology Stack

- **Backend**: Django 5.2.4, Python 3.12
- **Database**: PostgreSQL with TimescaleDB extension
- **Frontend**: Bootstrap 5, ApexCharts, DataTables
- **Message Queue**: MQTT for real-time data streaming
- **Package Management**: UV (Python package manager)
- **Authentication**: Django Allauth

## 📋 Prerequisites

- Python 3.12+
- PostgreSQL 14+ with TimescaleDB extension
- MQTT Broker (for real-time data)
- UV package manager

## 🔧 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/herambgvd/ai_opjindal.git
cd ai_opjindal
```

### 2. Install Dependencies
```bash
# Install UV if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync
```

### 3. Database Setup

#### Install TimescaleDB Extension
```sql
-- Connect to your PostgreSQL database
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
```

#### Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Configure your environment variables
export DJANGO_DATABASE_NAME="op_jindal"
export DJANGO_DATABASE_USER="postgres"
export DJANGO_DATABASE_PASSWORD="your_secure_password"
export DJANGO_DATABASE_HOST="localhost"
export DJANGO_DATABASE_PORT="5432"
```

### 4. Run Migrations
```bash
uv run python manage.py migrate
```

### 5. Create Superuser
```bash
uv run python manage.py createsuperuser
```

### 6. Start Development Server
```bash
uv run python manage.py runserver
```

## 🎯 Usage

### Starting the MQTT Consumer
To begin receiving real-time data from cameras:
```bash
uv run python manage.py mqtt_consumer
```

### Bulk Camera Upload via CSV
To upload multiple cameras at once:
1. Navigate to Django Admin: `http://localhost:8000/admin/cross_counting/camera/`
2. Click "Upload CSV" button
3. Select your CSV file with the required format:
   - **Required columns**: `name`, `region`
   - **Optional columns**: `status`, `rtsp_link`, `hls_link`
4. Review the upload results and any error messages

**Sample CSV format:**
```csv
name,region,status,rtsp_link,hls_link
CH1,Main Hall,true,rtsp://192.168.1.100:554/stream1,http://192.168.1.100:8080/hls/stream1.m3u8
CH2,Main Hall,true,rtsp://192.168.1.101:554/stream1,
CH3,Parking Area,false,rtsp://192.168.1.102:554/stream1,
```

A sample CSV file is included at `sample_cameras.csv` for testing purposes.

### Accessing the Platform
- **Main Dashboard**: `http://localhost:8000/`
- **Admin Panel**: `http://localhost:8000/admin/`
- **Analysis Views**: `http://localhost:8000/cross/analysis/`
- **Public Display**: `http://localhost:8000/cross/public/occupancy/`

### MQTT Payload Format
The system expects MQTT payloads in the following format:
```json
{
  "data": {
    "dev_net_info": [
      {
        "device_name": "GV-DNC575-AI",
        "mac": "8C-1F-64-D5-DB-EF",
        "ip": "172.17.41.211",
        "phy": "eth0",
        "ChannelName": "CH10"
      }
    ],
    "alarm_list": [
      {
        "time": "2025-07-31T07:46:02Z+05:30",
        "channel_alarm": [
          {
            "cc_alarm_num": {
              "cc_in_num": 59,
              "cc_out_num": 96,
              "cc_total_num": 155
            },
            "int_alarm": {
              "alarm_val": true,
              "int_subtype": "cc"
            },
            "channel": "CH1"
          }
        ]
      }
    ]
  }
}
```

## 📊 Database Schema

### Key Models

#### Region
- Manages location tags with occupancy limits
- Supports hierarchical organization of cameras

#### Camera
- Stores camera configuration and status
- Links to regions for organizational structure
- Tracks last data received timestamp

#### CrossCountingData (TimescaleDB Hypertable)
- High-frequency time-series data storage
- Optimized indexes for fast analytical queries
- Automatic partitioning by time intervals
- Compression and retention policies

## 🔍 Analysis Features

### Daily Analysis
- Select region and date for analysis
- View hourly trends with interactive charts
- Export detailed CSV reports
- Camera-wise peak count summaries

### Comparative Analysis
- Compare data between two specific dates
- Visual difference indicators
- Side-by-side metric comparisons
- Export comparison reports

### Comprehensive Analysis
- Analyze data over custom date ranges
- Daily trend visualization
- Multi-camera data aggregation
- Comprehensive CSV exports

## 📈 Performance Optimizations

### TimescaleDB Features
- **Hypertables**: Automatic time-based partitioning
- **Compression**: 7-day compression policy for older data
- **Retention**: 90-day data retention policy
- **Continuous Aggregates**: Pre-computed hourly and daily views
- **Optimized Indexes**: Time-series specific indexing strategies

### Query Optimization
- Materialized views for common aggregations
- BRIN indexes for time-based queries
- Efficient camera and region filtering
- Cached occupancy calculations

## 🎨 UI/UX Features

### Dashboard
- Real-time platform statistics
- System health monitoring
- Occupancy status overview
- Quick action buttons

### Public Display
- TV-optimized interface
- Beautiful card-based layout
- Auto-refresh functionality
- No authentication required
- Responsive design for different screen sizes

### Charts & Visualization
- Interactive ApexCharts integration
- Responsive chart rendering
- Multiple chart types (line, bar, comparison)
- Real-time data updates

## 🔒 Security Features

- Environment variable-based configuration
- No hardcoded credentials
- Secure authentication with Django Allauth
- Public endpoints with read-only access
- Input validation and sanitization

## 🚀 Deployment

### Production Checklist
1. Configure production database with TimescaleDB
2. Set secure environment variables
3. Configure MQTT broker connection
4. Set up SSL/TLS certificates
5. Configure static file serving
6. Set up monitoring and logging
7. Configure backup strategies

### Environment Variables
```bash
# Database Configuration
DJANGO_DATABASE_NAME=op_jindal
DJANGO_DATABASE_USER=postgres
DJANGO_DATABASE_PASSWORD=secure_password
DJANGO_DATABASE_HOST=localhost
DJANGO_DATABASE_PORT=5432

# Django Settings
DJANGO_SECRET_KEY=your_secret_key
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=your-domain.com

# MQTT Configuration (if needed)
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
```

## 📁 Project Structure

```
ai_opjindal/
├── apps/
│   ├── cross_counting/          # Core cross-counting functionality
│   │   ├── management/commands/ # MQTT consumer and utilities
│   │   ├── migrations/         # Database migrations
│   │   ├── views/              # Analysis, dashboard, and CRUD views
│   │   ├── models.py           # TimescaleDB-optimized models
│   │   ├── forms.py            # Analysis and management forms
│   │   ├── utils.py            # Analytics and utility functions
│   │   └── urls.py             # URL routing
│   ├── users/                  # User management
│   ├── web/                    # Landing pages and general views
│   └── utils/                  # Shared utilities
├── templates/                  # Django templates
│   ├── cross_counting/         # Analysis and management templates
│   ├── dashboard/              # Dashboard templates
│   └── partials/               # Reusable template components
├── static/                     # Static assets (CSS, JS, images)
├── opjindal/                   # Django project settings
└── manage.py                   # Django management script
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is proprietary software. All rights reserved.

## 🆘 Support

For support and questions, please contact the development team or create an issue in the repository.

## 🔄 Version History

- **v1.0.0** - Initial release with basic CRUD functionality
- **v2.0.0** - Added MQTT integration and cross-counting data model
- **v3.0.0** - Implemented analysis views with CSV export functionality
- **v4.0.0** - Added TimescaleDB integration and enhanced dashboard
- **v4.1.0** - Added public occupancy display and chart visualizations

---

**Built with ❤️ by the AI OpJindal Development Team**
