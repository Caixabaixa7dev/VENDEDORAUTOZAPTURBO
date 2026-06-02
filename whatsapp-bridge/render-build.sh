#!/usr/bin/env bash
set -e

echo "Installing npm dependencies..."
npm install

echo "Installing Puppeteer system dependencies..."
npx puppeteer browsers install chrome

echo "Build complete!"
