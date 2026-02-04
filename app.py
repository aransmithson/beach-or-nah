import streamlit as st
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
        max-width: 600px;
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
    
    .beach-container {
        position: relative;
        width: 100%;
        height: 400px;
        background: linear-gradient(180deg, #f4e4c1 0%, #d4b896 100%);
        border-radius: 20px;
        overflow: hidden;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
        margin: 30px 0;
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
    # Try direct readings endpoint first
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

def get_verdict(water_percent, is_rising):
    """Determine if it's beach weather or nah"""
    if water_percent < 30:
        return "BEACH!"
    elif water_percent < 60 and not is_rising:
        return "BEACH!"
    elif water_percent > 70:
        return "NAH."
    else:
        return "MAYBE?"

# Main app
def main():
    st.markdown('<div class="title">BEACH OR NAH?</div>', unsafe_allow_html=True)
    
    # User location input
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### 📍 Enter Your Location")
        
        # Auto-location button
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
        
        # Manual input fields with session state defaults
        default_lat = st.session_state.get('user_lat', 52.4767)
        default_lon = st.session_state.get('user_lon', 1.7514)
        
        user_lat = st.number_input("Latitude", value=default_lat, format="%.4f", key="lat")
        user_lon = st.number_input("Longitude", value=default_lon, format="%.4f", key="lon")
        
        # Update session state with manual inputs
        st.session_state['user_lat'] = user_lat
        st.session_state['user_lon'] = user_lon
        
        if st.button("🌊 Check Tide Conditions", use_container_width=True):
            with st.spinner("Finding your nearest beach..."):
                # Find nearest station
                station = find_nearest_tide_station(user_lat, user_lon)
                
                if not station:
                    st.error("❌ Could not find a nearby tide station")
                    return
                
                st.session_state['station'] = station
                
                # Get tide data
                tide_data = get_tide_data(station['id'])
                
                if not tide_data:
                    st.error(f"❌ Could not get tide data for {station['name']}")
                    return
                
                st.session_state['tide_data'] = tide_data
    
    # Display results if we have data
    if 'station' in st.session_state and 'tide_data' in st.session_state:
        station = st.session_state['station']
        tide_data = st.session_state['tide_data']
        
        # Location info
        st.markdown(
            f'<div class="location-info">{station["name"]} • {station["distance"]:.1f}km away</div>',
            unsafe_allow_html=True
        )
        
        # Calculate water percentage
        max_height = 8  # meters
        water_percent = min(max(tide_data['current_level'] / max_height * 100, 0), 100)
        
        # Verdict
        verdict = get_verdict(water_percent, tide_data['is_rising'])
        st.markdown(f'<div class="verdict">{verdict}</div>', unsafe_allow_html=True)
        
        # Tide info
        direction = "Rising ⬆️" if tide_data['is_rising'] else "Falling ⬇️"
        tide_time = datetime.fromisoformat(tide_data['time'].replace('Z', '+00:00'))
        
        st.markdown(f"""
        <div class="tide-info">
            <div style="display: flex; justify-content: space-around; align-items: center;">
                <div>
                    <div class="detail-label">Tide Status</div>
                    <div class="detail-value">{direction}</div>
                </div>
                <div>
                    <div class="detail-label">Height</div>
                    <div class="detail-value">{tide_data['current_level']:.2f}m</div>
                </div>
                <div>
                    <div class="detail-label">Time</div>
                    <div class="detail-value">{tide_time.strftime('%H:%M')}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Beach visualization
        st.markdown('<div class="beach-container">', unsafe_allow_html=True)
        
        # Create a simple visualization with colored bars
        col_beach, col_water = st.columns(2)
        
        with col_beach:
            st.markdown(f"""
            <div style="background: linear-gradient(180deg, #f4e4c1 0%, #d4b896 100%); 
                        height: {100-water_percent}%; 
                        display: flex; 
                        align-items: center; 
                        justify-content: center;
                        color: #1a4645;
                        font-family: 'Space Mono', monospace;
                        font-weight: 700;">
                🏖️ SAND ({100-water_percent:.0f}%)
            </div>
            """, unsafe_allow_html=True)
        
        with col_water:
            st.markdown(f"""
            <div style="background: linear-gradient(180deg, #7dd3c0 0%, #2a9d8f 100%); 
                        height: {water_percent}%; 
                        display: flex; 
                        align-items: center; 
                        justify-content: center;
                        color: white;
                        font-family: 'Space Mono', monospace;
                        font-weight: 700;">
                🌊 WATER ({water_percent:.0f}%)
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Debug panel (collapsible)
        with st.expander("📡 API Debug Info"):
            st.markdown('<div class="debug-panel">', unsafe_allow_html=True)
            
            st.markdown("**📍 Your Location:**")
            st.json({
                'latitude': user_lat,
                'longitude': user_lon
            })
            
            st.markdown("**🏖️ Selected Station:**")
            st.json({
                'selectedNearestStation': station,
                'distanceKm': f"{station['distance']:.2f}"
            })
            
            st.markdown("**🌊 Tide Readings:**")
            st.json(tide_data['raw_data'])
            
            st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
