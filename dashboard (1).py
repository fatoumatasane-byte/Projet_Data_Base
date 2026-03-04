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

# ================================================================
#  CUSTOM CSS
# ================================================================
st.markdown("""
<style>
    /* Fond général */
    .stApp {
        background-color: #f0f7f0;
    }

    /* Titre principal */
    h1 {
        color: #1a5c2a !important;
        font-family: 'Georgia', serif;
        border-bottom: 3px solid #4CAF50;
        padding-bottom: 10px;
    }

    h2, h3 {
        color: #2e7d32 !important;
    }

    /* Cartes KPI */
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, #1a5c2a, #2e7d32);
        border-radius: 12px;
        padding: 20px;
        border-left: 5px solid #f9a825;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }

    [data-testid="metric-container"] label {
        color: #c8e6c9 !important;
        font-size: 14px !important;
        font-weight: 600;
    }

    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-size: 32px !important;
        font-weight: 700;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab"] {
        background-color: #c8e6c9;
        border-radius: 8px 8px 0 0;
        color: #1a5c2a;
        font-weight: 600;
        padding: 8px 20px;
    }

    .stTabs [aria-selected="true"] {
        background-color: #2e7d32 !important;
        color: white !important;
    }

    /* Dataframe */
    [data-testid="stDataFrame"] {
        border: 2px solid #4CAF50;
        border-radius: 8px;
    }

    /* Divider */
    hr {
        border: none;
        border-top: 2px solid #4CAF50;
        margin: 20px 0;
    }

    /* Subheader styling */
    .section-title {
        background: linear-gradient(90deg, #2e7d32, #66bb6a);
        color: white;
        padding: 8px 16px;
        border-radius: 8px;
        font-size: 18px;
        font-weight: 700;
        margin-bottom: 12px;
    }

    /* Footer */
    .footer {
        text-align: center;
        color: #558b2f;
        font-size: 13px;
        margin-top: 30px;
        padding: 10px;
        border-top: 2px solid #4CAF50;
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

# Couleurs du thème pour les graphiques
COLORS_GREEN = ['#1b5e20', '#2e7d32', '#388e3c', '#43a047', '#66bb6a', '#a5d6a7']
COLORS_MIXED = ['#2e7d32', '#f9a825', '#1565c0', '#b71c1c', '#6a1b9a', '#00695c']

# ================================================================
#  EN-TETE
# ================================================================
col_logo, col_title = st.columns([1, 5])
with col_logo:
    st.markdown("## 🌿")
with col_title:
    st.markdown("# IoT Agricultural Monitoring Dashboard")
    st.markdown("**AIMS Sénégal — 2025** | Secure IoT-Based Agricultural Monitoring System")

st.markdown("---")

# ================================================================
#  KPIs
# ================================================================
st.markdown('<div class="section-title">📊 Key Performance Indicators</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

total_fields = run_query("SELECT COUNT(*) AS n FROM Fields").iloc[0]['n']
col1.metric("🌾 Total Active Fields", total_fields)

water = run_query("SELECT ROUND(SUM(irraterVolume_m3), 1) AS t FROM IrrigationEvents").iloc[0]['t']
col2.metric("🚿 Total Water Usage", f"{water or 0} m³")

alerts = run_query("SELECT COUNT(*) AS n FROM Alerts WHERE resolved = 0").iloc[0]['n']
col3.metric("🚨 Active Alerts", alerts)

st.markdown("---")

# ================================================================
#  GRAPHIQUES
# ================================================================
st.markdown('<div class="section-title">📈 Visualizations</div>', unsafe_allow_html=True)
st.markdown("")

col_left, col_right = st.columns(2)

# Yield par culture
with col_left:
    st.markdown("#### 🌽 Yield by Crop (tons)")
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
            color_discrete_sequence=COLORS_GREEN
        )
        fig.update_layout(
            showlegend=False, height=350,
            plot_bgcolor='rgba(240,247,240,0.8)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#1a5c2a'),
            xaxis=dict(gridcolor='#c8e6c9'),
            yaxis=dict(gridcolor='#c8e6c9')
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No yield data available.")

# Irrigation par parcelle
with col_right:
    st.markdown("#### 🚿 Irrigation Events by Field (m³)")
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
        fig.update_layout(
            showlegend=False, height=350,
            plot_bgcolor='rgba(240,247,240,0.8)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#1a5c2a'),
            xaxis=dict(gridcolor='#c8e6c9'),
            yaxis=dict(gridcolor='#c8e6c9')
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No irrigation data available.")

st.markdown("---")

# ================================================================
#  ANALYSE — QUESTIONS DU PROF
# ================================================================
st.markdown('<div class="section-title">🔍 Database Analysis</div>', unsafe_allow_html=True)
st.markdown("")

tab1, tab2 = st.tabs([
    "📊 Q1 — Highest Yield per Hectare",
    "⚠️ Q2 — Fields with Most Anomalies"
])

with tab1:
    st.markdown("**Which crops produce the highest average yield (tons/hectare) across all farms?**")
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
            color_discrete_sequence=COLORS_GREEN
        )
        fig.update_layout(
            showlegend=False, height=300,
            plot_bgcolor='rgba(240,247,240,0.8)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#1a5c2a'),
            xaxis=dict(gridcolor='#c8e6c9'),
            yaxis=dict(gridcolor='#c8e6c9')
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data available.")

with tab2:
    st.markdown("**Which fields experience the highest frequency of sensor anomalies?**")
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
        fig.update_layout(
            showlegend=False, height=300,
            plot_bgcolor='rgba(240,247,240,0.8)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#1a5c2a'),
            xaxis=dict(gridcolor='#c8e6c9'),
            yaxis=dict(gridcolor='#c8e6c9')
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No sensor data available.")

# ================================================================
#  FOOTER
# ================================================================
st.markdown(
    '<div class="footer">🌿 IoT Agricultural Monitoring System — AIMS Sénégal 2025</div>',
    unsafe_allow_html=True
)
