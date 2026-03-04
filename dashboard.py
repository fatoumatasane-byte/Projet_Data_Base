import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# ================================================================
#  CONFIGURATION
# ================================================================
st.set_page_config(
    page_title="IoT Agricultural Monitoring",
    page_icon="🌱",
    layout="wide"
)

# ================================================================
#  CONNEXION A LA BASE DE DONNEES
# ================================================================
DB_PATH = "iot_agri.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def run_query(sql):
    conn = get_connection()
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df

# ================================================================
#  TITRE
# ================================================================
st.title("🌱 IoT Agricultural Monitoring Dashboard")
st.markdown("**AIMS Sénégal — 2025** | Système de Monitoring Agricole")
st.markdown("---")

# ================================================================
#  KPI — INDICATEURS CLES
# ================================================================
st.subheader("📊 Key Performance Indicators")

col1, col2, col3, col4, col5 = st.columns(5)

# Total Active Fields
total_fields = run_query("SELECT COUNT(*) AS n FROM Fields").iloc[0]['n']
col1.metric("🌾 Total Fields", total_fields)

# Average Soil Moisture
avg_moisture = run_query("""
    SELECT ROUND(AVG(value), 1) AS avg_val
    FROM SensorReadings
    WHERE metricType = 'soil_moisture'
""").iloc[0]['avg_val']
avg_moisture = avg_moisture if avg_moisture else "N/A"
col2.metric("💧 Avg Soil Moisture", f"{avg_moisture} %" if avg_moisture != "N/A" else "N/A")

# Water Usage (total)
water_usage = run_query("""
    SELECT ROUND(SUM(irraterVolume_m3), 1) AS total
    FROM IrrigationEvents
""").iloc[0]['total']
water_usage = water_usage if water_usage else 0
col3.metric("🚿 Total Water Usage", f"{water_usage} m³")

# Yield Projection
yield_proj = run_query("""
    SELECT ROUND(SUM(yieldTons), 1) AS total
    FROM CropCycles
    WHERE yieldTons IS NOT NULL
""").iloc[0]['total']
yield_proj = yield_proj if yield_proj else 0
col4.metric("📈 Total Yield", f"{yield_proj} t")

# Active Alerts
active_alerts = run_query("""
    SELECT COUNT(*) AS n FROM Alerts WHERE resolved = 0
""").iloc[0]['n']
col5.metric("🚨 Active Alerts", active_alerts)

st.markdown("---")

# ================================================================
#  GRAPHIQUES — LIGNE 1
# ================================================================
col_left, col_right = st.columns(2)

# --- Graphique 1 : Yield par culture ---
with col_left:
    st.subheader("🌽 Yield by Crop (tons)")
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
            color='cropName',
            labels={'cropName': 'Crop', 'totalYield': 'Total Yield (tons)'},
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig.update_layout(showlegend=False, height=350)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No yield data available.")

# --- Graphique 2 : Alertes par severite ---
with col_right:
    st.subheader("🚨 Alerts by Severity")
    df_alerts = run_query("""
        SELECT severity, COUNT(*) AS nb
        FROM Alerts
        GROUP BY severity
    """)
    if not df_alerts.empty:
        color_map = {'Critical': '#d62728', 'High': '#ff7f0e',
                     'Medium': '#ffdd57', 'Low': '#2ca02c'}
        fig = px.pie(
            df_alerts, names='severity', values='nb',
            color='severity', color_discrete_map=color_map,
            hole=0.4
        )
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No alert data available.")

# ================================================================
#  GRAPHIQUES — LIGNE 2
# ================================================================
col_left2, col_right2 = st.columns(2)

# --- Graphique 3 : Irrigation par parcelle ---
with col_left2:
    st.subheader("🚿 Water Usage by Field (m³)")
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
            color_discrete_sequence=['#1f77b4']
        )
        fig.update_layout(showlegend=False, height=350)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No irrigation data available.")

# --- Graphique 4 : Status des dispositifs IoT ---
with col_right2:
    st.subheader("📡 IoT Device Status")
    df_devices = run_query("""
        SELECT deviceStatus, COUNT(*) AS nb
        FROM IoTDevices
        GROUP BY deviceStatus
    """)
    if not df_devices.empty:
        color_map2 = {'Active': '#2ca02c', 'Faulty': '#d62728', 'Inactive': '#7f7f7f'}
        fig = px.pie(
            df_devices, names='deviceStatus', values='nb',
            color='deviceStatus', color_discrete_map=color_map2,
            hole=0.4
        )
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No device data available.")

st.markdown("---")

# ================================================================
#  ANALYSE DE BASE DE DONNEES
# ================================================================
st.subheader("🔍 Database Analysis")

tab1, tab2 = st.tabs([
    "Q1 — Highest Average Yield per Hectare",
    "Q2 — Fields with Most Sensor Anomalies"
])

# --- Q1 : Cultures avec le meilleur rendement moyen ---
with tab1:
    st.markdown("**Which crops produce the highest average yield (tons/hectare) across all farms?**")
    df_q1 = run_query("""
        SELECT
            c.cropName,
            ROUND(AVG(cc.yieldTons), 2)            AS avgYield_tons,
            ROUND(AVG(f.area_ha), 2)               AS avgArea_ha,
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
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig.update_layout(showlegend=False, height=300)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data available.")

# --- Q2 : Parcelles avec le plus d'anomalies ---
with tab2:
    st.markdown("**Which fields experience the highest frequency of sensor anomalies?**")
    df_q2 = run_query("""
        SELECT
            f.name                                          AS fieldName,
            COUNT(sr.readingId)                            AS totalReadings,
            SUM(sr.anomalyFlag)                            AS totalAnomalies,
            ROUND(SUM(sr.anomalyFlag) * 100.0
                  / COUNT(sr.readingId), 1)                AS anomalyRate_pct
        FROM SensorReadings sr
        JOIN IoTDevices d ON sr.deviceId  = d.deviceId
        JOIN Fields     f ON d.fieldId    = f.fieldId
        GROUP BY f.name
        ORDER BY anomalyRate_pct DESC
    """)
    if not df_q2.empty:
        st.dataframe(df_q2, use_container_width=True)
        fig = px.bar(
            df_q2, x='fieldName', y='anomalyRate_pct',
            labels={'fieldName': 'Field', 'anomalyRate_pct': 'Anomaly Rate (%)'},
            color_discrete_sequence=['#d62728']
        )
        fig.update_layout(showlegend=False, height=300)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No sensor data available.")

st.markdown("---")

# ================================================================
#  TABLES DE DETAILS
# ================================================================
st.subheader("📋 Data Tables")

tab_a, tab_b, tab_c = st.tabs(["Alerts", "IoT Devices", "Irrigation Events"])

with tab_a:
    df_al = run_query("""
        SELECT a.alertId, f.name AS field, a.alertType,
               a.severity, a.message, a.createdAt,
               CASE WHEN a.resolved = 1 THEN 'Yes' ELSE 'No' END AS resolved
        FROM Alerts a
        JOIN Fields f ON a.fieldId = f.fieldId
        ORDER BY a.createdAt DESC
    """)
    st.dataframe(df_al, use_container_width=True)

with tab_b:
    df_dev = run_query("""
        SELECT d.deviceId, d.deviceType, d.deviceSerialNumber,
               f.name AS field, d.firmwareVersion,
               d.lastSeen, d.deviceStatus
        FROM IoTDevices d
        JOIN Fields f ON d.fieldId = f.fieldId
    """)
    st.dataframe(df_dev, use_container_width=True)

with tab_c:
    df_irr2 = run_query("""
        SELECT ie.irrigId, f.name AS field,
               ie.irrigStartTime, ie.irrigEndTime,
               ie.irraterVolume_m3 AS volume_m3,
               CASE WHEN ie.irrigAutomated = 1 THEN 'Yes' ELSE 'No' END AS automated
        FROM IrrigationEvents ie
        JOIN Fields f ON ie.fieldId = f.fieldId
    """)
    st.dataframe(df_irr2, use_container_width=True)

st.caption("IoT Agricultural Monitoring System — AIMS Sénégal 2025")
