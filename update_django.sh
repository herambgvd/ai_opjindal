#!/bin/bash
# Script to update Django to version 4.2.16 LTS for PostgreSQL 12 compatibility

echo "Updating Django to 4.2.16 LTS for PostgreSQL 12 compatibility..."

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install the downgraded Django version
pip install Django==4.2.16

# Install all requirements to ensure compatibility
pip install -r requirements.txt

# Run migrations to ensure database compatibility
python manage.py migrate

echo "Django downgrade completed successfully!"
echo "You can now restart your server."
