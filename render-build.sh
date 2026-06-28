#!/usr/bin/env bash
# render-build.sh - Build script for Render

set -o errexit  # Exit on error
set -o pipefail # Exit on pipe failure

echo "========================================="
echo "Starting build process..."
echo "========================================="

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Run migrations
echo "🔄 Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "========================================="
echo "✅ Build completed successfully!"
echo "========================================="