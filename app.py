import streamlit as st
import streamlit.components.v1 as components
import requests
from datetime import datetime
import math
import time
from streamlit_js_eval import get_geolocation

# Page configuration
st.set_page_config(
    page_title="Beach or Nah?",
    page_icon="🏖️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for trendy design
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Space+Mono:wght@400;700&display=swap');

    .main {
        background: linear-gradient(180deg, #ffd6ba 0%, #f4e4c1 100%);
    }

    .title {
        font-family: 'Bebas Neue', sans-serif;
        font-size: 72px;
        color: #ffffff;
        text-align: center;
        letter-spacing: 8px;
        text-shadow: 4px 4px 12px rgba(0,0,0,0.4);
        margin-bottom: 0;
    }

    .location-info {
        text-align: center;
        color: #1a4645;
        font-family: 'Space Mono', monospace;
        font-size: 14px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-top: 10px;
    }

    .verdict {
        font-family: 'Bebas Neue', sans-serif;
        font-size: 120px;
        text-align: center;
        background: linear-gradient(135deg, #ffd700, #ffed4e);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        filter: drop-shadow(0 0 20px rgba(255, 215, 0, 0.5));
        letter-spacing: 6px;
        margin: 20px 0;
    }

    .tide-info {
        font-family: 'Space Mono', monospace;
        background: rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(10px);
        padding: 20px;
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        color: white;
        text-align: center;
        margin: 20px auto;
        max-width: 800px;
    }

    .weather-info {
        font-family: 'Space Mono', monospace;
        background: rgba(42, 157, 143, 0.25);
        backdrop-filter: blur(10px);
        padding: 20px;
        border-radius: 20px;
        border: 1px solid rgba(42, 157, 143, 0.4);
        color: white;
        text-align: center;
        margin: 20px auto;
        max-width: 800px;
    }

    .detail-label {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: rgba(255, 255, 255, 0.7);
        margin-bottom: 5px;
    }

    .detail-value {
        font-size: 24px;
        font-weight: 700;
        color: white;
    }

    .weather-icon {
        font-size: 48px;
        display: block;
        margin-bottom: 5px;
    }

    .debug-panel {
        background: rgba(0, 0, 0, 0.9);
        color: #7dd3c0;
        padding: 20px;
        border-radius: 10px;
        font-family: 'Space Mono', monospace;
        font-size: 11px;
        margin-top: 20px;
    }

    .stButton>button {
        font-family: 'Space Mono', monospace;
        background: #2a9d8f;
        color: white;
        border: none;
        padding: 12px 30px;
        border-radius: 25px;
        font-weight: 700;
        letter-spacing: 1px;
    }
</style>
<script defer src='https://static.cloudflareinsights.com/beacon.min.js' data-cf-beacon='{"token": "7eb348d6a4d64d1595ba7ed828a4ad13"}'></script>
""", unsafe_allow_html=True)


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates in km"""
    R = 6371  # Earth's radius in km

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c


def find_nearest_tide_station(lat, lon):
    """Find the nearest tide gauge station"""
    url = "https://environment.data.gov.uk/flood-monitoring/id/stations?type=TideGauge&_limit=1000"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data.get('items'):
            return None

        nearest_station = None
        min_distance = float('inf')

        for station in data['items']:
            if station.get('lat') and station.get('long'):
                distance = calculate_distance(lat, lon, station['lat'], station['long'])

                if distance < min_distance:
                    min_distance = distance
                    nearest_station = {
                        'id': station.get('stationReference') or station.get('notation'),
                        'name': station.get('label'),
                        'lat': station.get('lat'),
                        'long': station.get('long'),
                        'town': station.get('town'),
                        'distance': distance,
                        'full_data': station
                    }

        return nearest_station

    except Exception as e:
        st.error(f"Error fetching stations: {str(e)}")
        return None


def get_tide_data(station_id):
    """Get current tide data for a station"""
    url = f"https://environment.data.gov.uk/flood-monitoring/id/stations/{station_id}/readings?_sorted&_limit=10"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get('items') and len(data['items']) >= 2:
            latest = data['items'][0]
            previous = data['items'][1]

            return {
                'current_level': latest['value'],
                'previous_level': previous['value'],
                'time': latest['dateTime'],
                'is_rising': latest['value'] > previous['value'],
                'raw_data': data
            }

        # If no items, try getting station details first
        station_url = f"https://environment.data.gov.uk/flood-monitoring/id/stations/{station_id}"
        station_response = requests.get(station_url, timeout=10)
        station_data = station_response.json()

        # Look for measures
        if station_data.get('measures'):
            for measure in station_data['measures']:
                measure_id = measure.get('@id')
                if 'level' in measure_id.lower() or 'tidal' in measure_id.lower():
                    readings_url = f"{measure_id}/readings?_sorted&_limit=10"
                    readings_response = requests.get(readings_url, timeout=10)
                    readings_data = readings_response.json()

                    if readings_data.get('items') and len(readings_data['items']) >= 2:
                        latest = readings_data['items'][0]
                        previous = readings_data['items'][1]

                        return {
                            'current_level': latest['value'],
                            'previous_level': previous['value'],
                            'time': latest['dateTime'],
                            'is_rising': latest['value'] > previous['value'],
                            'raw_data': readings_data
                        }

        return None

    except Exception as e:
        st.error(f"Error fetching tide data: {str(e)}")
        return None


def get_weather_data(lat, lon, api_key):
    """Get current weather from OpenWeatherMap"""
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        wind_speed_kmh = data['wind']['speed'] * 3.6  # m/s → km/h

        return {
            'temp': data['main']['temp'],
            'feels_like': data['main']['feels_like'],
            'humidity': data['main']['humidity'],
            'wind_speed': wind_speed_kmh,
            'wind_deg': data['wind'].get('deg', 0),
            'description': data['weather'][0]['description'].title(),
            'condition': data['weather'][0]['main'],
            'icon_code': data['weather'][0]['icon'],
            'city': data.get('name', ''),
            'visibility': data.get('visibility', 10000) / 1000,
            'raw_data': data
        }
    except Exception as e:
        st.warning(f"⚠️ Could not fetch weather data: {str(e)}")
        return None


def weather_emoji(condition, icon_code):
    """Map OpenWeather condition to emoji"""
    mapping = {
        'Thunderstorm': '⛈️',
        'Drizzle': '🌦️',
        'Rain': '🌧️',
        'Snow': '❄️',
        'Mist': '🌫️',
        'Fog': '🌫️',
        'Haze': '🌫️',
        'Clear': '☀️',
        'Clouds': '⛅' if '02' in icon_code or '03' in icon_code else '☁️',
    }
    return mapping.get(condition, '🌤️')


def wind_direction_label(deg):
    """Convert wind degrees to compass label"""
    dirs = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
    idx = round(deg / 45) % 8
    return dirs[idx]


def get_verdict(water_percent, is_rising, weather=None):
    """Determine if it's beach weather or nah, factoring in both tide and weather"""
    # Base verdict from tide
    if water_percent < 30:
        tide_verdict = "BEACH!"
    elif water_percent < 60 and not is_rising:
        tide_verdict = "BEACH!"
    elif water_percent > 70:
        tide_verdict = "NAH."
    else:
        tide_verdict = "MAYBE?"

    if weather is None:
        return tide_verdict

    # Weather overrides
    bad_conditions = ['Thunderstorm', 'Rain', 'Drizzle', 'Snow']
    if weather['condition'] in bad_conditions:
        return "NAH."
    if weather['wind_speed'] > 55:
        return "NAH."
    if weather['wind_speed'] > 35 and tide_verdict == "BEACH!":
        return "MAYBE?"
    if weather['temp'] < 10:
        return "NAH." if tide_verdict == "BEACH!" else tide_verdict
    if weather['temp'] < 15 and tide_verdict == "BEACH!":
        return "MAYBE?"

    return tide_verdict


def render_wave_animation(water_percent, is_rising, weather=None):
    """Render an animated canvas wave scene"""
    wind_speed = weather.get('wind_speed', 10) if weather else 10
    condition = weather.get('condition', 'Clear') if weather else 'Clear'
    temp = weather.get('temp', 20) if weather else 20

    # Wave drama: amplitude grows with tide level and wind
    base_amplitude = 18 + (water_percent / 100) * 55
    wind_boost = min(wind_speed / 60, 1.0) * 30
    amplitude = base_amplitude + wind_boost

    # More wave layers when it's windy/stormy
    wave_layers = 4 if wind_speed > 30 or condition in ['Thunderstorm', 'Rain'] else 3

    # Sky colours based on conditions
    if condition == 'Thunderstorm':
        sky_top, sky_bot = '#2c2c3a', '#4a4a5a'
        show_sun = 'false'
    elif condition in ['Rain', 'Drizzle']:
        sky_top, sky_bot = '#7a8fa6', '#b0c4d8'
        show_sun = 'false'
    elif condition == 'Clouds':
        sky_top, sky_bot = '#a8c0d6', '#d4e8f0'
        show_sun = 'false'
    else:
        sky_top = '#87CEEB'
        sky_bot = '#f4e4c1'
        show_sun = 'true'

    # Seabird count — more when windy
    num_birds = 3 if wind_speed > 20 else 1

    html = f"""
<canvas id="beachCanvas" width="1200" height="400"
    style="width:100%; height:400px; border-radius:20px; display:block;"></canvas>
<script>
(function() {{
    const canvas = document.getElementById('beachCanvas');
    const ctx = canvas.getContext('2d');
    const W = canvas.width;
    const H = canvas.height;

    const WATER_PCT   = {water_percent:.2f};
    const AMPLITUDE   = {amplitude:.2f};
    const WAVE_LAYERS = {wave_layers};
    const WIND        = {wind_speed:.2f};
    const SHOW_SUN    = {show_sun};
    const NUM_BIRDS   = {num_birds};
    const RISING      = {'true' if is_rising else 'false'};

    // Seabird state
    const birds = Array.from({{length: NUM_BIRDS}}, (_, i) => ({{
        x: Math.random() * W,
        y: H * 0.08 + Math.random() * H * 0.18,
        speed: 0.4 + Math.random() * 0.6 + WIND * 0.015,
        amp: 8 + Math.random() * 12,
        freq: 0.015 + Math.random() * 0.01,
        phase: Math.random() * Math.PI * 2,
        size: 6 + Math.random() * 5
    }}));

    let t = 0;

    function drawSun() {{
        const cx = W * 0.84, cy = H * 0.18, r = 38;
        // Glow
        const glow = ctx.createRadialGradient(cx, cy, r * 0.2, cx, cy, r * 2.5);
        glow.addColorStop(0, 'rgba(255,230,50,0.35)');
        glow.addColorStop(1, 'rgba(255,200,30,0)');
        ctx.beginPath();
        ctx.arc(cx, cy, r * 2.5, 0, Math.PI * 2);
        ctx.fillStyle = glow;
        ctx.fill();
        // Core
        const core = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
        core.addColorStop(0,   'rgba(255,245,150,1)');
        core.addColorStop(0.5, 'rgba(255,220,50,1)');
        core.addColorStop(1,   'rgba(255,180,0,0.85)');
        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.fillStyle = core;
        ctx.fill();
    }}

    function drawSky() {{
        const sky = ctx.createLinearGradient(0, 0, 0, H * 0.55);
        sky.addColorStop(0, '{sky_top}');
        sky.addColorStop(1, '{sky_bot}');
        ctx.fillStyle = sky;
        ctx.fillRect(0, 0, W, H);
    }}

    function drawSand() {{
        const sandLine = H * 0.58;
        const sand = ctx.createLinearGradient(0, sandLine, 0, H);
        sand.addColorStop(0, '#f4e4c1');
        sand.addColorStop(0.4, '#e8d5a8');
        sand.addColorStop(1,   '#c9a87a');
        ctx.fillStyle = sand;
        ctx.fillRect(0, sandLine, W, H - sandLine);

        // Subtle sand texture lines
        ctx.strokeStyle = 'rgba(180,140,80,0.18)';
        ctx.lineWidth = 1;
        for (let i = 0; i < 6; i++) {{
            const y = sandLine + 20 + i * 28;
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.bezierCurveTo(W*0.25, y+4, W*0.75, y-4, W, y);
            ctx.stroke();
        }}
    }}

    function waveY(x, layer, time) {{
        const speed  = 0.018 + layer * 0.008;
        const freq1  = (WAVE_LAYERS + 2) + layer * 0.8;
        const freq2  = WAVE_LAYERS + layer * 0.5;
        const amp    = AMPLITUDE * (0.55 + layer * 0.22);
        const phase  = layer * 0.9;
        return amp * Math.sin((x / W) * Math.PI * freq1 + time * speed * 60 + phase)
             + amp * 0.38 * Math.sin((x / W) * Math.PI * freq2 + time * (speed + 0.009) * 60);
    }}

    function drawWaves(time) {{
        const waterBase = H * (1 - WATER_PCT / 100);

        for (let layer = WAVE_LAYERS - 1; layer >= 0; layer--) {{
            const alpha = 0.38 + layer * 0.18;
            const r = layer % 2 === 0 ? 42 : 28;
            const g = layer % 2 === 0 ? 157 : 180;
            const b = layer % 2 === 0 ? 143 : 200;

            ctx.beginPath();
            ctx.moveTo(0, H);

            for (let x = 0; x <= W; x += 4) {{
                ctx.lineTo(x, waterBase + waveY(x, layer, time));
            }}

            ctx.lineTo(W, H);
            ctx.closePath();

            const grad = ctx.createLinearGradient(0, waterBase - AMPLITUDE, 0, H);
            grad.addColorStop(0, `rgba(${{r}},${{g}},${{b}},${{alpha}})`);
            grad.addColorStop(0.5, `rgba(15,90,100,0.88)`);
            grad.addColorStop(1,   `rgba(8,50,60,0.95)`);
            ctx.fillStyle = grad;
            ctx.fill();
        }}

        // Foam crest on top wave
        ctx.save();
        ctx.strokeStyle = 'rgba(255,255,255,0.75)';
        ctx.lineWidth = 2.5;
        ctx.shadowBlur = 6;
        ctx.shadowColor = 'rgba(255,255,255,0.5)';
        ctx.beginPath();
        for (let x = 0; x <= W; x += 4) {{
            const y = waterBase + waveY(x, 0, time);
            x === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        }}
        ctx.stroke();
        ctx.restore();

        // Secondary foam line
        ctx.strokeStyle = 'rgba(255,255,255,0.35)';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        for (let x = 0; x <= W; x += 4) {{
            const y = waterBase + waveY(x, 1, time) + 12;
            x === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        }}
        ctx.stroke();
    }}

    function drawBirds(time) {{
        ctx.fillStyle = 'rgba(30,30,50,0.8)';
        birds.forEach(b => {{
            b.x += b.speed;
            if (b.x > W + 30) b.x = -30;
            const by = b.y + Math.sin(time * b.freq * 60 + b.phase) * b.amp;
            const wingFlap = Math.sin(time * 0.08 * 60 + b.phase) * b.size * 0.5;

            // Simple gull silhouette: two arcs
            ctx.beginPath();
            ctx.moveTo(b.x, by);
            ctx.quadraticCurveTo(b.x - b.size, by - b.size * 0.8 + wingFlap, b.x - b.size * 2.2, by);
            ctx.moveTo(b.x, by);
            ctx.quadraticCurveTo(b.x + b.size, by - b.size * 0.8 + wingFlap, b.x + b.size * 2.2, by);
            ctx.lineWidth = 1.5;
            ctx.strokeStyle = 'rgba(30,30,50,0.75)';
            ctx.stroke();
        }});
    }}

    function drawTideArrow(time) {{
        // Small animated tide direction arrow near the waterline
        const waterBase = H * (1 - WATER_PCT / 100);
        const arrowX = W * 0.06;
        const arrowY = waterBase + 10;
        const bounce = Math.sin(time * 0.05 * 60) * 5;
        const dy = RISING ? -1 : 1;

        ctx.save();
        ctx.globalAlpha = 0.8;
        ctx.fillStyle = RISING ? '#7dd3c0' : '#f4a261';
        ctx.font = 'bold 22px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(RISING ? '▲' : '▼', arrowX, arrowY + bounce);
        ctx.restore();
    }}

    function frame() {{
        drawSky();
        if (SHOW_SUN) drawSun();
        drawSand();
        drawWaves(t);
        drawBirds(t);
        drawTideArrow(t);
        t += 0.016;
        requestAnimationFrame(frame);
    }}

    frame();
}})();
</script>
"""
    return html


# ─── Main app ────────────────────────────────────────────────────────────────
def main():
    st.markdown('<div class="title">BEACH OR NAH?</div>', unsafe_allow_html=True)

    # ── OpenWeather API key ──────────────────────────────────────────────────
    # Try secrets first, fall back to sidebar input
    ow_api_key = None
    try:
        ow_api_key = st.secrets["OPENWEATHER_API_KEY"]
    except Exception:
        pass

    if not ow_api_key:
        with st.sidebar:
            st.markdown("### 🌤️ OpenWeather API Key")
            st.markdown(
                "Get a free key at [openweathermap.org](https://openweathermap.org/api). "
                "Or add it to `.streamlit/secrets.toml` as `OPENWEATHER_API_KEY`."
            )
            ow_api_key = st.text_input(
                "API Key", type="password",
                placeholder="Paste your OpenWeather key here",
                key="ow_key_input"
            ) or None

    # ── Location input ───────────────────────────────────────────────────────
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("### 📍 Enter Your Location")

        if st.button("📍 Use My Current Location", use_container_width=True, type="primary"):
            with st.spinner("Getting your location..."):
                try:
                    location = get_geolocation()
                    if location and 'coords' in location:
                        st.session_state['user_lat'] = location['coords']['latitude']
                        st.session_state['user_lon'] = location['coords']['longitude']
                        st.success(f"✅ Location found: {location['coords']['latitude']:.4f}, {location['coords']['longitude']:.4f}")
                    else:
                        st.warning("⚠️ Could not get your location. Please enable location services or enter manually.")
                except Exception as e:
                    st.warning(f"⚠️ Could not get your location: {str(e)}. Please enter manually.")

        default_lat = st.session_state.get('user_lat', 52.4767)
        default_lon = st.session_state.get('user_lon', 1.7514)

        user_lat = st.number_input("Latitude",  value=default_lat, format="%.4f", key="lat")
        user_lon = st.number_input("Longitude", value=default_lon, format="%.4f", key="lon")

        st.session_state['user_lat'] = user_lat
        st.session_state['user_lon'] = user_lon

        if st.button("🌊 Check Conditions", use_container_width=True):
            with st.spinner("Finding your nearest beach..."):
                station = find_nearest_tide_station(user_lat, user_lon)
                if not station:
                    st.error("❌ Could not find a nearby tide station")
                    return
                st.session_state['station'] = station

                tide_data = get_tide_data(station['id'])
                if not tide_data:
                    st.error(f"❌ Could not get tide data for {station['name']}")
                    return
                st.session_state['tide_data'] = tide_data

                # Fetch weather if we have an API key
                if ow_api_key:
                    weather = get_weather_data(user_lat, user_lon, ow_api_key)
                    st.session_state['weather'] = weather
                else:
                    st.session_state['weather'] = None

    # ── Results ──────────────────────────────────────────────────────────────
    if 'station' in st.session_state and 'tide_data' in st.session_state:
        station   = st.session_state['station']
        tide_data = st.session_state['tide_data']
        weather   = st.session_state.get('weather')

        # Location header
        st.markdown(
            f'<div class="location-info">{station["name"]} • {station["distance"]:.1f}km away</div>',
            unsafe_allow_html=True
        )

        # Calculate water percentage
        max_height   = 8
        water_percent = min(max(tide_data['current_level'] / max_height * 100, 0), 100)

        # Verdict (weather-aware)
        verdict = get_verdict(water_percent, tide_data['is_rising'], weather)
        st.markdown(f'<div class="verdict">{verdict}</div>', unsafe_allow_html=True)

        # ── Weather panel ────────────────────────────────────────────────────
        if weather:
            emoji = weather_emoji(weather['condition'], weather['icon_code'])
            wind_dir = wind_direction_label(weather['wind_deg'])
            st.markdown(f"""
            <div class="weather-info">
                <div style="font-size:13px; text-transform:uppercase; letter-spacing:2px;
                            color:rgba(255,255,255,0.6); margin-bottom:14px;">
                    🌤️ Current Weather — {weather['city']}
                </div>
                <div style="display:flex; justify-content:space-around; align-items:center; flex-wrap:wrap; gap:10px;">
                    <div>
                        <span class="weather-icon">{emoji}</span>
                        <div class="detail-value" style="font-size:16px;">{weather['description']}</div>
                    </div>
                    <div>
                        <div class="detail-label">Temp</div>
                        <div class="detail-value">{weather['temp']:.0f}°C</div>
                        <div style="font-size:12px; color:rgba(255,255,255,0.5);">
                            feels {weather['feels_like']:.0f}°C
                        </div>
                    </div>
                    <div>
                        <div class="detail-label">Wind</div>
                        <div class="detail-value">{weather['wind_speed']:.0f} km/h</div>
                        <div style="font-size:12px; color:rgba(255,255,255,0.5);">{wind_dir}</div>
                    </div>
                    <div>
                        <div class="detail-label">Humidity</div>
                        <div class="detail-value">{weather['humidity']}%</div>
                    </div>
                    <div>
                        <div class="detail-label">Visibility</div>
                        <div class="detail-value">{weather['visibility']:.0f} km</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        elif not ow_api_key:
            st.info("💡 Add an OpenWeather API key in the sidebar to get live weather conditions.")

        # ── Tide panel ───────────────────────────────────────────────────────
        direction = "Rising ⬆️" if tide_data['is_rising'] else "Falling ⬇️"
        tide_time = datetime.fromisoformat(tide_data['time'].replace('Z', '+00:00'))

        st.markdown(f"""
        <div class="tide-info">
            <div style="font-size:13px; text-transform:uppercase; letter-spacing:2px;
                        color:rgba(255,255,255,0.6); margin-bottom:14px;">
                🌊 Tide Conditions — {station['name']}
            </div>
            <div style="display:flex; justify-content:space-around; align-items:center;">
                <div>
                    <div class="detail-label">Tide Status</div>
                    <div class="detail-value">{direction}</div>
                </div>
                <div>
                    <div class="detail-label">Height</div>
                    <div class="detail-value">{tide_data['current_level']:.2f}m</div>
                </div>
                <div>
                    <div class="detail-label">Beach Coverage</div>
                    <div class="detail-value">{water_percent:.0f}%</div>
                </div>
                <div>
                    <div class="detail-label">Time</div>
                    <div class="detail-value">{tide_time.strftime('%H:%M')}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Animated wave scene ──────────────────────────────────────────────
        wave_html = render_wave_animation(water_percent, tide_data['is_rising'], weather)
        components.html(wave_html, height=420)

        # ── Debug panel ──────────────────────────────────────────────────────
        with st.expander("📡 API Debug Info"):
            st.markdown('<div class="debug-panel">', unsafe_allow_html=True)

            st.markdown("**📍 Your Location:**")
            st.json({'latitude': user_lat, 'longitude': user_lon})

            st.markdown("**🏖️ Selected Station:**")
            st.json({'selectedNearestStation': station, 'distanceKm': f"{station['distance']:.2f}"})

            st.markdown("**🌊 Tide Readings:**")
            st.json(tide_data['raw_data'])

            if weather:
                st.markdown("**🌤️ Weather Data:**")
                st.json(weather['raw_data'])

            st.markdown('</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
