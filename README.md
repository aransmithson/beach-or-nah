# Beach or Nah? 🏖️

A trendy zero-click tide monitoring app built with Python and Streamlit.

## Features

- 📍 **Auto Location Detection** - One click to use your current location
- 🌊 Real-time tide data from UK Environment Agency API
- 🎨 Trendy retro-futuristic design
- 📊 Visual beach/water ratio display

## Installation

1. Install the required packages:
```bash
pip install -r requirements.txt
```

## Running the App

```bash
streamlit run app.py
```

## How to Use

### Auto-Location (Recommended)
Click "📍 Use My Current Location"

The app will:
- Find the nearest UK tide gauge station
- Fetch real-time tide data
- Display the current tide status
- Show you the verdict: Beach or Nah?

## Browser Location Requirements

For auto-location to work:
- Your browser must support geolocation (all modern browsers do)
- You must be using HTTPS or localhost
- You need to allow location permissions when prompted

## API Details

The app uses the UK Environment Agency Flood Monitoring API:
- **Stations Endpoint**: `https://environment.data.gov.uk/flood-monitoring/id/stations`
- **Readings Endpoint**: `https://environment.data.gov.uk/flood-monitoring/id/stations/{id}/readings`

All API responses are visible in the debug panel at the bottom of the app.


## Design

- Font: Bebas Neue (headers) + Space Mono (body)
- Color scheme: Sunset sand and ocean gradients
- Retro terminal-style debug panel
- Responsive layout

Enjoy your beach days! 🌊☀️
