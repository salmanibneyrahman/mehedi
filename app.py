import streamlit as st
import requests
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import time
import numpy as np
from datetime import datetime
import json

# Config
ESP32_IP = "192.168.1.105"  # ← CHANGE TO YOUR ESP32 IP
REFRESH_INTERVAL = 2  # seconds

# Page config
st.set_page_config(
    page_title="Solar Monitoring Dashboard",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header { font-size: 3rem; color: #00d4ff; text-align: center; margin-bottom: 2rem; }
    .metric-card { background: linear-gradient(135deg, #1a1a2e, #16213e); border-radius: 15px; padding: 1.5rem; }
    .status-online { background: linear-gradient(90deg, #00ff88, #00d4ff); }
    .status-offline { background: linear-gradient(90deg, #ff4757, #ff6b9d); }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'sensor_data' not in st.session_state:
    st.session_state.sensor_data = {}
if 'data_history' not in st.session_state:
    st.session_state.data_history = {key: [] for key in ['dc_v', 'dc_i', 'ac_v', 'ac_i', 'inv_v', 'temp', 'humid']}
if 'timestamps' not in st.session_state:
    st.session_state.timestamps = []

def fetch_sensor_data():
    try:
        response = requests.get(f"http://{ESP32_IP}/data", timeout=5)
        if response.status_code == 200:
            data = response.json()
            data['timestamp'] = datetime.now()
            st.session_state.connection_status = "🟢 ONLINE"
            return data
        else:
            st.session_state.connection_status = "🔴 OFFLINE"
            return None
    except:
        st.session_state.connection_status = "🔴 OFFLINE"
        return None

def update_data_history(data, max_points=50):
    keys = ['dc_v', 'dc_i', 'ac_v', 'ac_i', 'inv_v', 'temp', 'humid']
    st.session_state.timestamps.append(datetime.now())
    for key in keys:
        if key in data:
            st.session_state.data_history[key].append(float(data[key]))
            if len(st.session_state.data_history[key]) > max_points:
                st.session_state.data_history[key].pop(0)
    if len(st.session_state.timestamps) > max_points:
        st.session_state.timestamps.pop(0)

# Auto-refresh
if st.button("🔄 Refresh Now") or st.session_state.get('auto_refresh', True):
    data = fetch_sensor_data()
    if data:
        st.session_state.sensor_data = data
        update_data_history(data)

# Header
st.markdown('<h1 class="main-header">☀️ Solar Data Monitoring</h1>', unsafe_allow_html=True)
st.markdown(f"**BRAC University** | {st.session_state.get('connection_status', '🔴 Connecting...')}")

# Main dashboard
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("""
    <div class="metric-card status-online">
        <h3>DC Voltage</h3>
        <h1>{:.1f} V</h1>
    </div>
    """.format(st.session_state.sensor_data.get('dc_v', 0)), unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="metric-card status-online">
        <h3>DC Current</h3>
        <h1>{:.2f} A</h1>
    </div>
    """.format(st.session_state.sensor_data.get('dc_i', 0)), unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="metric-card status-online">
        <h3>AC Voltage</h3>
        <h1>{:.1f} V</h1>
    </div>
    """.format(st.session_state.sensor_data.get('ac_v', 0)), unsafe_allow_html=True)

with col4:
    st.markdown("""
    <div class="metric-card status-online">
        <h3>Temperature</h3>
        <h1>{:.1f}°C</h1>
    </div>
    """.format(st.session_state.sensor_data.get('temp', 0)), unsafe_allow_html=True)

# Charts row
col1, col2 = st.columns(2)

with col1:
    # DC Power Chart
    if st.session_state.data_history['dc_v']:
        df_dc = pd.DataFrame({
            'Time': st.session_state.timestamps[-50:],
            'Vdc': st.session_state.data_history['dc_v'][-50:],
            'Idc': st.session_state.data_history['dc_i'][-50:]
        })
        fig_dc = px.line(df_dc, x='Time', y=['Vdc', 'Idc'], 
                        title="DC Parameters", color_discrete_map={'Vdc': '#00ff88', 'Idc': '#00d4ff'})
        fig_dc.update_layout(height=300, showlegend=True)
        st.plotly_chart(fig_dc, use_container_width=True)

with col2:
    # AC Parameters
    if st.session_state.data_history['ac_v']:
        df_ac = pd.DataFrame({
            'Time': st.session_state.timestamps[-50:],
            'Vac': st.session_state.data_history['ac_v'][-50:],
            'Iac': st.session_state.data_history['ac_i'][-50:]
        })
        fig_ac = px.line(df_ac, x='Time', y=['Vac', 'Iac'],
                        title="AC Parameters", color_discrete_map={'Vac': '#ff6b9d', 'Iac': '#ffd93d'})
        fig_ac.update_layout(height=300, showlegend=True)
        st.plotly_chart(fig_ac, use_container_width=True)

# Environment + Balance
col1, col2 = st.columns(2)

with col1:
    # Environment
    if st.session_state.data_history['temp']:
        df_env = pd.DataFrame({
            'Time': st.session_state.timestamps[-50:],
            'Temp': st.session_state.data_history['temp'][-50:],
            'Humidity': st.session_state.data_history['humid'][-50:]
        })
        fig_env = px.line(df_env, x='Time', y=['Temp', 'Humidity'], 
                         title="Environment", color_discrete_map={'Temp': '#ff4757', 'Humidity': '#00cec9'})
        fig_env.update_layout(height=300)
        st.plotly_chart(fig_env, use_container_width=True)

with col2:
    # Energy Balance
    dc_power = np.array(st.session_state.data_history['dc_v'][-50:]) * np.array(st.session_state.data_history['dc_i'][-50:])
    ac_power = np.array(st.session_state.data_history['ac_v'][-50:]) * np.array(st.session_state.data_history['ac_i'][-50:])
    
    df_power = pd.DataFrame({
        'Time': st.session_state.timestamps[-50:],
        'DC Power': dc_power,
        'AC Power': ac_power
    })
    
    fig_power = px.line(df_power, x='Time', y=['DC Power', 'AC Power'],
                       title="Power Analysis", color_discrete_map={'DC Power': '#ffd93d', 'AC Power': '#00ff88'})
    fig_power.update_layout(height=300)
    st.plotly_chart(fig_power, use_container_width=True)

# Auto-refresh placeholder
st.markdown("---")
st.caption(f"⏱️ Auto-refreshing every {REFRESH_INTERVAL}s | Last update: {datetime.now().strftime('%H:%M:%S')}")
