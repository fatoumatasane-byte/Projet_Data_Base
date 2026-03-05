import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import os

# ── Page config ──────────────────────────────────────────────────
st.set_page_config(page_title="IoT Agricultural Monitoring", page_icon="🌿", layout="wide")

st.markdown("""
<style>
  .kpi-card {
    background: linear-gradient(135deg, #1b5e20, #388e3c);
    border-left: 5px solid #f9a825;
    border-radius: 10px;
    padding: 18px 20px;
    color: white;
    text-align: center;
    margin-bottom: 8px;
  }
  .kpi-value { font-size: 2rem; font-weight: bold; margin: 0; }
  .kpi-label { font-size: 0.85rem; opacity: 0.85; margin: 0; }
  .kpi-sub   { font-size: 0.75rem; opacity: 0.65; margin: 0; }
</style>
""", unsafe_allow_html=True)

# ── DB connection ─────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "iot_agri.db")

@st.cache_resource
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def run_query(sql):
    return pd.read_sql_query(sql, get_conn())

# ── Header ────────────────────────────────────────────────────────
st.markdown("## 🌿 IoT Agricultural Monitoring Dashboard")
st.caption("AIMS Sénégal — 2025 | Secure IoT-Based Agricultural Monitoring System")
st.divider()

# ══════════════════════════════════════════════════════════════════
# KPIs
# ══════════════════════════════════════════════════════════════════
st.markdown("### 📊 Key Performance Indicators")

fields   = run_query("SELECT COUNT(DISTINCT fieldId) AS n FROM IoTDevices").iloc[0]['n']
moisture = run_query("SELECT ROUND(AVG(value),1) AS v FROM SensorReadings WHERE metricType='soil_moisture'").iloc[0]['v']
water    = run_query("SELECT ROUND(SUM(waterVolume_m3),1) AS v FROM IrrigationEvents").iloc[0]['v']
yield_t  = run_query("SELECT ROUND(SUM(yieldTons),1) AS v FROM CropCycles WHERE status='Completed'").iloc[0]['v']
alerts_n = run_query("SELECT COUNT(*) AS n FROM Alerts WHERE resolved=0").iloc[0]['n']

c1, c2, c3, c4, c5 = st.columns(5)
for col, val, label, sub in [
    (c1, int(fields),    "Active Fields",     "With IoT devices"),
    (c2, f"{moisture} %","Avg Soil Moisture", "All sensors"),
    (c3, f"{water} m³",  "Total Water Used",  "All irrigation events"),
    (c4, f"{yield_t} t", "Total Yield",       "Completed cycles"),
    (c5, int(alerts_n),  "Active Alerts",     "Unresolved"),
]:
    with col:
        st.markdown(f'<div class="kpi-card"><p class="kpi-value">{val}</p><p class="kpi-label">{label}</p><p class="kpi-sub">{sub}</p></div>', unsafe_allow_html=True)

st.divider()

# ══════════════════════════════════════════════════════════════════
# CHARTS
# ══════════════════════════════════════════════════════════════════
st.markdown("### 📈 Visualizations")
col1, col2 = st.columns(2)

# Soil Moisture Trend
with col1:
    st.markdown("##### 💧 Soil Moisture Trend")
    df_sm = run_query("""
        SELECT sr.readingId, sr.value, sr.anomalyFlag, f.name AS field
        FROM SensorReadings sr
        JOIN IoTDevices d ON sr.deviceId = d.deviceId
        JOIN Fields f ON d.fieldId = f.fieldId
        WHERE sr.metricType = 'soil_moisture'
        ORDER BY sr.readingId
    """)
    if not df_sm.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_sm['readingId'], y=df_sm['value'],
            mode='lines+markers', name='Soil Moisture',
            line=dict(color='#4caf50', width=2), marker=dict(size=6)))
        anom = df_sm[df_sm['anomalyFlag'] == 1]
        if not anom.empty:
            fig.add_trace(go.Scatter(x=anom['readingId'], y=anom['value'],
                mode='markers', name='⚠ Anomaly',
                marker=dict(color='red', size=12, symbol='x')))
        fig.add_hline(y=18, line_dash='dash', line_color='orange',
                      annotation_text='Min 18%')
        fig.update_layout(xaxis_title='Reading #', yaxis_title='Moisture (%)',
            plot_bgcolor='white', paper_bgcolor='white', margin=dict(t=20,b=40))
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"⚠ {len(anom)} anomaly/anomalies detected")

# Temperature Trend
with col2:
    st.markdown("##### 🌡️ Temperature Trend")
    df_temp = run_query("""
        SELECT sr.readingId, sr.value, sr.anomalyFlag, f.name AS field
        FROM SensorReadings sr
        JOIN IoTDevices d ON sr.deviceId = d.deviceId
        JOIN Fields f ON d.fieldId = f.fieldId
        WHERE sr.metricType = 'temperature'
        ORDER BY sr.readingId
    """)
    if not df_temp.empty:
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=df_temp['readingId'], y=df_temp['value'],
            mode='lines+markers', name='Temperature',
            line=dict(color='#ff9800', width=2), marker=dict(size=6)))
        anom_t = df_temp[df_temp['anomalyFlag'] == 1]
        if not anom_t.empty:
            fig2.add_trace(go.Scatter(x=anom_t['readingId'], y=anom_t['value'],
                mode='markers', name='⚠ Anomaly',
                marker=dict(color='red', size=12, symbol='x')))
        fig2.add_hline(y=35, line_dash='dash', line_color='red',
                       annotation_text='Max 35°C')
        fig2.update_layout(xaxis_title='Reading #', yaxis_title='Temp (°C)',
            plot_bgcolor='white', paper_bgcolor='white', margin=dict(t=20,b=40))
        st.plotly_chart(fig2, use_container_width=True)
        st.caption(f"⚠ {len(anom_t)} anomaly/anomalies detected")
    else:
        st.info("No temperature readings found.")

col3, col4 = st.columns(2)

# Irrigation Events
with col3:
    st.markdown("##### 🚿 Irrigation Events")
    df_irr = run_query("""
        SELECT ie.irrigId, f.name AS field,
               ie.irrigStartTime, ie.waterVolume_m3, ie.irrigAutomated
        FROM IrrigationEvents ie
        JOIN Fields f ON ie.fieldId = f.fieldId
        ORDER BY ie.irrigStartTime
    """)
    if not df_irr.empty:
        fig3 = px.bar(df_irr, x='irrigStartTime', y='waterVolume_m3',
            color='field', barmode='group',
            color_discrete_sequence=px.colors.qualitative.Set2,
            labels={'waterVolume_m3': 'Volume (m³)', 'irrigStartTime': 'Date', 'field': 'Field'})
        fig3.update_layout(plot_bgcolor='white', paper_bgcolor='white',
            legend=dict(orientation='h', y=-0.3), margin=dict(t=20,b=60))
        st.plotly_chart(fig3, use_container_width=True)

# Yield by Crop
with col4:
    st.markdown("##### 🌽 Yield by Crop (tons)")
    df_yield = run_query("""
        SELECT c.cropName, ROUND(SUM(cc.yieldTons),1) AS totalYield
        FROM CropCycles cc
        JOIN Crops c ON cc.cropId = c.cropId
        WHERE cc.yieldTons IS NOT NULL
        GROUP BY c.cropName ORDER BY totalYield DESC
    """)
    if not df_yield.empty:
        fig4 = px.bar(df_yield, x='cropName', y='totalYield',
            color='cropName',
            color_discrete_sequence=['#2e7d32','#66bb6a','#a5d6a7','#1b5e20','#81c784'],
            labels={'totalYield': 'Total Yield (t)', 'cropName': 'Crop'})
        fig4.update_layout(plot_bgcolor='white', paper_bgcolor='white',
            showlegend=False, margin=dict(t=20,b=40))
        st.plotly_chart(fig4, use_container_width=True)

st.divider()

# ══════════════════════════════════════════════════════════════════
# DATABASE ANALYSIS
# ══════════════════════════════════════════════════════════════════
st.markdown("### 🔍 Database Analysis")
col5, col6 = st.columns(2)

# Q1
with col5:
    st.markdown("##### Q1 — Highest Average Yield per Hectare")
    df_q1 = run_query("""
        SELECT c.cropName AS Crop,
               ROUND(AVG(cc.yieldTons), 2)                     AS "Avg Yield (t)",
               ROUND(AVG(f.area_ha), 2)                        AS "Avg Area (ha)",
               ROUND(AVG(cc.yieldTons) / AVG(f.area_ha), 2)    AS "Yield/ha (t/ha)"
        FROM CropCycles cc
        JOIN Crops c  ON cc.cropId  = c.cropId
        JOIN Fields f ON cc.fieldId = f.fieldId
        WHERE cc.yieldTons IS NOT NULL
        GROUP BY c.cropName
        ORDER BY "Yield/ha (t/ha)" DESC
    """)
    st.dataframe(df_q1, use_container_width=True, hide_index=True)
    if not df_q1.empty:
        fig_q1 = px.bar(df_q1, x='Crop', y='Yield/ha (t/ha)', color='Crop',
            color_discrete_sequence=['#2e7d32','#66bb6a','#a5d6a7','#1b5e20'])
        fig_q1.update_layout(plot_bgcolor='white', paper_bgcolor='white',
            showlegend=False, margin=dict(t=20,b=40))
        st.plotly_chart(fig_q1, use_container_width=True)

# Q2
with col6:
    st.markdown("##### Q2 — Fields with Highest Anomaly Rate")
    df_q2 = run_query("""
        SELECT f.name AS Field,
               COUNT(*) AS "Total Readings",
               SUM(sr.anomalyFlag) AS "Anomalies",
               ROUND(100.0 * SUM(sr.anomalyFlag) / COUNT(*), 1) AS "Anomaly Rate (%)"
        FROM SensorReadings sr
        JOIN IoTDevices d ON sr.deviceId = d.deviceId
        JOIN Fields f     ON d.fieldId   = f.fieldId
        GROUP BY f.name
        ORDER BY "Anomaly Rate (%)" DESC
    """)
    st.dataframe(df_q2, use_container_width=True, hide_index=True)
    if not df_q2.empty:
        fig_q2 = px.bar(df_q2, x='Field', y='Anomaly Rate (%)', color='Field',
            color_discrete_sequence=px.colors.qualitative.Set2)
        fig_q2.update_layout(plot_bgcolor='white', paper_bgcolor='white',
            showlegend=False, margin=dict(t=20,b=40))
        st.plotly_chart(fig_q2, use_container_width=True)

st.divider()

# Active Alerts table
st.markdown("### 🚨 Active Alerts")
df_alerts = run_query("""
    SELECT a.alertId AS ID, f.name AS Field, a.alertType AS Type,
           a.severity AS Severity, a.message AS Message, a.createdAt AS Date
    FROM Alerts a
    JOIN Fields f ON a.fieldId = f.fieldId
    WHERE a.resolved = 0
    ORDER BY a.createdAt DESC
""")
if not df_alerts.empty:
    st.dataframe(df_alerts, use_container_width=True, hide_index=True)
else:
    st.success("✅ No active alerts.")

st.divider()
st.caption("IoT Agricultural Monitoring System — AIMS Sénégal 2025")
