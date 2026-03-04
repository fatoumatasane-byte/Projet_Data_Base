import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px

# ================================================================
#  CONFIGURATION
# ================================================================
st.set_page_config(
    page_title="IoT Agricultural Monitoring",
    page_icon="🌿",
    layout="wide"
)

# CSS minimal — uniquement les KPI cards
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

COLORS = ['#1b5e20', '#2e7d32', '#43a047', '#66bb6a', '#a5d6a7']

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

col1, col2, col3 = st.columns(3)

total_fields = run_query("SELECT COUNT(*) AS n FROM Fields").iloc[0]['n']
col1.metric("🌾 Total Active Fields", total_fields)

water = run_query("SELECT ROUND(SUM(irraterVolume_m3), 1) AS t FROM IrrigationEvents").iloc[0]['t']
col2.metric("🚿 Total Water Usage", f"{water or 0} m³")

alerts = run_query("SELECT COUNT(*) AS n FROM Alerts WHERE resolved = 0").iloc[0]['n']
col3.metric("🚨 Active Alerts", int(alerts))

st.divider()

# ================================================================
#  GRAPHIQUES
# ================================================================
st.subheader("📈 Visualizations")

col_left, col_right = st.columns(2)

with col_left:
    st.write("#### 🌽 Yield by Crop (tons)")
    df_yield = run_query("""
        SELECT c.cropName, ROUND(SUM(cc.yieldTons), 2) AS totalYield
        FROM CropCycles cc
        JOIN Crops c ON cc.cropId = c.cropId
        WHERE cc.yieldTons IS NOT NULL
        GROUP BY c.cropName
    """)
    if not df_yield.empty:
        fig = px.bar(
            df_yield, x='cropName', y='totalYield',
            labels={'cropName': 'Crop', 'totalYield': 'Total Yield (tons)'},
            color='cropName',
            color_discrete_sequence=COLORS
        )
        fig.update_layout(showlegend=False, height=350)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No yield data available.")

with col_right:
    st.write("#### 🚿 Irrigation by Field (m³)")
    df_irr = run_query("""
        SELECT f.name AS fieldName,
               ROUND(SUM(ie.irraterVolume_m3), 1) AS totalWater
        FROM IrrigationEvents ie
        JOIN Fields f ON ie.fieldId = f.fieldId
        GROUP BY f.name
        ORDER BY totalWater DESC
    """)
    if not df_irr.empty:
        fig = px.bar(
            df_irr, x='fieldName', y='totalWater',
            labels={'fieldName': 'Field', 'totalWater': 'Water (m³)'},
            color='fieldName',
            color_discrete_sequence=['#f9a825', '#fb8c00']
        )
        fig.update_layout(showlegend=False, height=350)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No irrigation data available.")

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
               ROUND(AVG(cc.yieldTons / f.area_ha), 2) AS avgYield_per_ha
        FROM CropCycles cc
        JOIN Crops  c ON cc.cropId  = c.cropId
        JOIN Fields f ON cc.fieldId = f.fieldId
        WHERE cc.yieldTons IS NOT NULL
        GROUP BY c.cropName
        ORDER BY avgYield_per_ha DESC
    """)
    if not df_q1.empty:
        st.dataframe(df_q1, use_container_width=True)
        fig = px.bar(
            df_q1, x='cropName', y='avgYield_per_ha',
            labels={'cropName': 'Crop', 'avgYield_per_ha': 'Avg Yield (t/ha)'},
            color='cropName',
            color_discrete_sequence=COLORS
        )
        fig.update_layout(showlegend=False, height=300)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data available.")

with tab2:
    st.write("**Which fields experience the highest frequency of sensor anomalies?**")
    df_q2 = run_query("""
        SELECT f.name AS fieldName,
               COUNT(sr.readingId)  AS totalReadings,
               SUM(sr.anomalyFlag)  AS totalAnomalies,
               ROUND(SUM(sr.anomalyFlag) * 100.0 / COUNT(sr.readingId), 1) AS anomalyRate_pct
        FROM SensorReadings sr
        JOIN IoTDevices d ON sr.deviceId = d.deviceId
        JOIN Fields     f ON d.fieldId   = f.fieldId
        GROUP BY f.name
        ORDER BY anomalyRate_pct DESC
    """)
    if not df_q2.empty:
        st.dataframe(df_q2, use_container_width=True)
        fig = px.bar(
            df_q2, x='fieldName', y='anomalyRate_pct',
            labels={'fieldName': 'Field', 'anomalyRate_pct': 'Anomaly Rate (%)'},
            color_discrete_sequence=['#b71c1c']
        )
        fig.update_layout(showlegend=False, height=300)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No sensor data available.")

st.divider()
st.caption("🌿 IoT Agricultural Monitoring System — AIMS Sénégal 2025")
