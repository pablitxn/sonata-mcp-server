#!/bin/bash
# scripts/setup_arch.sh

echo "Setting up MCP Government Connector on Arch Linux"

# Install system dependencies
echo "Installing system dependencies..."
sudo pacman -S --needed \
    python \
    cairo \
    pango \
    gdk-pixbuf2 \
    atk \
    gtk3 \
    nss \
    libxss \
    libxrandr \
    alsa-lib \
    libxcomposite \
    libxdamage \
    mesa \
    ffmpeg

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
fi

# Install Python dependencies
echo "Installing Python dependencies..."
poetry install

# Install Playwright browsers
echo "Installing Playwright browsers..."
poetry run playwright install chromium
poetry run playwright install-deps

# Create necessary directories
echo "Creating directories..."
mkdir -p states logs

echo "Setup complete!"