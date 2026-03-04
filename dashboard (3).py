import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ================================================================
#  CONFIGURATION
# ================================================================
st.set_page_config(
    page_title="IoT Agricultural Monitoring",
    page_icon="🌿",
    layout="wide"
)

st.markdown("""
<style>
[data-testid="metric-container"] {
    background: linear-gradient(135deg, #1b5e20, #388e3c);
    border-radius: 12px;
    padding: 16px;
    border-left: 5px solid #f9a825;
    box-shadow: 0 4px 10px rgba(0,0,0,0.2);
}
[data-testid="stMetricLabel"] > div {
    color: #e8f5e9 !important;
    font-size: 15px !important;
    font-weight: 600;
}
[data-testid="stMetricValue"] > div {
    color: #ffffff !important;
    font-size: 34px !important;
    font-weight: 800;
}
</style>
""", unsafe_allow_html=True)

# ================================================================
#  CONNEXION BASE DE DONNEES
# ================================================================
DB_PATH = "iot_agri.db"

def run_query(sql):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df

COLORS_GREEN  = ['#1b5e20', '#2e7d32', '#43a047', '#66bb6a', '#a5d6a7']
COLORS_ORANGE = ['#f9a825', '#fb8c00', '#e65100']
COLORS_MIXED  = ['#1b5e20', '#f9a825', '#1565c0', '#b71c1c']

# ================================================================
#  TITRE
# ================================================================
st.title("🌿 IoT Agricultural Monitoring Dashboard")
st.write("**AIMS Sénégal — 2025** | Secure IoT-Based Agricultural Monitoring System")
st.divider()

# ================================================================
#  KPIs
# ================================================================
st.subheader("📊 Key Performance Indicators")

col1, col2, col3, col4, col5 = st.columns(5)

total_fields = run_query("SELECT COUNT(*) AS n FROM Fields").iloc[0]['n']
col1.metric("🌾 Total Active Fields", total_fields)

avg_moisture = run_query("""
    SELECT ROUND(AVG(value), 1) AS avg_val
    FROM SensorReadings WHERE metricType = 'soil_moisture'
""").iloc[0]['avg_val']
col2.metric("💧 Avg Soil Moisture", f"{avg_moisture or 0} %")

water = run_query("""
    SELECT ROUND(SUM(irraterVolume_m3), 1) AS t FROM IrrigationEvents
""").iloc[0]['t']
col3.metric("🚿 Water Usage Today", f"{water or 0} m³")

yield_val = run_query("""
    SELECT ROUND(SUM(yieldTons), 1) AS t
    FROM CropCycles WHERE yieldTons IS NOT NULL
""").iloc[0]['t']
col4.metric("📈 Yield Projection", f"{yield_val or 0} t")

alerts = run_query("SELECT COUNT(*) AS n FROM Alerts WHERE resolved = 0").iloc[0]['n']
col5.metric("🚨 Active Alerts", int(alerts))

st.divider()

# ================================================================
#  GRAPHIQUES — LIGNE 1
# ================================================================
st.subheader("📈 Visualizations")

col_left, col_right = st.columns(2)

# --- Moisture graph ---
with col_left:
    st.write("#### 💧 Soil Moisture Trend")
    df_moist = run_query("""
        SELECT sr.readingId AS id,
               sr.value     AS moisture,
               sr.anomalyFlag
        FROM SensorReadings sr
        WHERE sr.metricType = 'soil_moisture'
        ORDER BY sr.readingId
    """)
    if not df_moist.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_moist['id'], y=df_moist['moisture'],
            mode='lines+markers',
            line=dict(color='#2e7d32', width=2),
            marker=dict(
                color=['#b71c1c' if a == 1 else '#2e7d32'
                       for a in df_moist['anomalyFlag']],
                size=8
            ),
            name='Soil Moisture (%)'
        ))
        fig.add_hline(y=20, line_dash='dash', line_color='#f9a825',
                      annotation_text='Min threshold (20%)')
        fig.update_layout(
            height=350,
            xaxis_title='Reading #',
            yaxis_title='Moisture (%)',
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption("🔴 Red markers = anomalies detected")
    else:
        st.info("No moisture data available.")

# --- Temperature trend ---
with col_right:
    st.write("#### 🌡️ Temperature Trend")
    df_temp = run_query("""
        SELECT sr.readingId AS id,
               sr.value     AS temperature,
               sr.anomalyFlag
        FROM SensorReadings sr
        WHERE sr.metricType = 'temperature'
        ORDER BY sr.readingId
    """)
    if not df_temp.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_temp['id'], y=df_temp['temperature'],
            mode='lines+markers',
            line=dict(color='#e65100', width=2),
            marker=dict(
                color=['#b71c1c' if a == 1 else '#e65100'
                       for a in df_temp['anomalyFlag']],
                size=8
            ),
            name='Temperature (C)'
        ))
        fig.add_hline(y=35, line_dash='dash', line_color='#b71c1c',
                      annotation_text='Max threshold (35°C)')
        fig.update_layout(
            height=350,
            xaxis_title='Reading #',
            yaxis_title='Temperature (°C)',
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption("🔴 Red markers = anomalies detected")
    else:
        st.info("No temperature data available.")

# ================================================================
#  GRAPHIQUES — LIGNE 2
# ================================================================
col_left2, col_right2 = st.columns(2)

# --- Irrigation Events Overlay ---
with col_left2:
    st.write("#### 🚿 Irrigation Events Overlay")
    df_irr = run_query("""
        SELECT ie.irrigId,
               f.name AS fieldName,
               ie.irrigStartTime,
               ie.irraterVolume_m3 AS volume_m3,
               CASE WHEN ie.irrigAutomated = 1
                    THEN 'Automated' ELSE 'Manual' END AS irrigType
        FROM IrrigationEvents ie
        JOIN Fields f ON ie.fieldId = f.fieldId
        ORDER BY ie.irrigStartTime
    """)
    if not df_irr.empty:
        fig = px.bar(
            df_irr, x='irrigStartTime', y='volume_m3',
            color='fieldName', barmode='group',
            labels={'irrigStartTime': 'Date',
                    'volume_m3': 'Water Volume (m³)',
                    'fieldName': 'Field'},
            color_discrete_sequence=COLORS_ORANGE
        )
        fig.update_layout(height=350, bargap=0.3)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No irrigation data available.")

# --- Yield by Crop ---
with col_right2:
    st.write("#### 🌽 Yield by Crop (tons)")
    df_yield = run_query("""
        SELECT c.cropName,
               ROUND(SUM(cc.yieldTons), 2) AS totalYield
        FROM CropCycles cc
        JOIN Crops c ON cc.cropId = c.cropId
        WHERE cc.yieldTons IS NOT NULL
        GROUP BY c.cropName
        ORDER BY totalYield DESC
    """)
    if not df_yield.empty:
        fig = px.bar(
            df_yield, x='cropName', y='totalYield',
            labels={'cropName': 'Crop', 'totalYield': 'Total Yield (tons)'},
            color='cropName',
            color_discrete_sequence=COLORS_GREEN
        )
        fig.update_layout(showlegend=False, height=350)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No yield data available.")

st.divider()

# ================================================================
#  ANALYSE — QUESTIONS DU PROF
# ================================================================
st.subheader("🔍 Database Analysis")

tab1, tab2 = st.tabs([
    "Q1 — Highest Yield per Hectare",
    "Q2 — Fields with Most Anomalies"
])

with tab1:
    st.write("**Which crops produce the highest average yield (tons/hectare)?**")
    df_q1 = run_query("""
        SELECT c.cropName,
               ROUND(AVG(cc.yieldTons), 2)             AS avgYield_tons,
               ROUND(AVG(f.area_ha), 2)                AS avgField_ha,
               ROUND(AVG(cc.yieldTons / f.area_ha), 2) AS avgYield_per_ha
        FROM CropCycles cc
        JOIN Crops  c ON cc.cropId  = c.cropId
        JOIN Fields f ON cc.fieldId = f.fieldId
        WHERE cc.yieldTons IS NOT NULL
        GROUP BY c.cropName
        ORDER BY avgYield_per_ha DESC
    """)
    if not df_q1.empty:
        col_t, col_g = st.columns([1, 2])
        with col_t:
            st.dataframe(df_q1, use_container_width=True)
        with col_g:
            fig = px.bar(
                df_q1, x='cropName', y='avgYield_per_ha',
                labels={'cropName': 'Crop', 'avgYield_per_ha': 'Avg Yield (t/ha)'},
                color='cropName',
                color_discrete_sequence=COLORS_GREEN
            )
            fig.update_layout(showlegend=False, height=280)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data available.")

with tab2:
    st.write("**Which fields experience the highest frequency of sensor anomalies?**")
    df_q2 = run_query("""
        SELECT f.name AS fieldName,
               COUNT(sr.readingId) AS totalReadings,
               SUM(sr.anomalyFlag) AS totalAnomalies,
               ROUND(SUM(sr.anomalyFlag) * 100.0
                     / COUNT(sr.readingId), 1) AS anomalyRate_pct
        FROM SensorReadings sr
        JOIN IoTDevices d ON sr.deviceId = d.deviceId
        JOIN Fields     f ON d.fieldId   = f.fieldId
        GROUP BY f.name
        ORDER BY anomalyRate_pct DESC
    """)
    if not df_q2.empty:
        col_t, col_g = st.columns([1, 2])
        with col_t:
            st.dataframe(df_q2, use_container_width=True)
        with col_g:
            fig = px.bar(
                df_q2, x='fieldName', y='anomalyRate_pct',
                labels={'fieldName': 'Field',
                        'anomalyRate_pct': 'Anomaly Rate (%)'},
                color_discrete_sequence=['#b71c1c']
            )
            fig.update_layout(showlegend=False, height=280)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No sensor data available.")

st.divider()
st.caption("🌿 IoT Agricultural Monitoring System — AIMS Sénégal 2025")
