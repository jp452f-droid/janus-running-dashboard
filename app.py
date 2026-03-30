import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from openai import OpenAI

# =========================
# 🔑 CONFIG
# =========================
CLIENT_ID = "218387"
CLIENT_SECRET = "8a9c83285b07d6ea26e6640d0fea8d90c87c7c14"
REFRESH_TOKEN = "75f956afd3c6b740cef3cf3c0b42a731b41d6009"

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# =========================
# 🔄 TOKEN
# =========================
def refresh_access_token():
    url = "https://www.strava.com/oauth/token"
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "grant_type": "refresh_token"
    }
    res = requests.post(url, data=payload)
    return res.json().get("access_token")

# =========================
# 📥 GET DATA
# =========================
def get_activities(token):
    url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(url, headers=headers)
    return res.json()

# =========================
# 🚀 UI
# =========================
st.set_page_config(page_title="Janus AI Running Coach", layout="wide")
st.title("🏃 Janus AI Running Dashboard")

access_token = refresh_access_token()
data = get_activities(access_token)

df = pd.DataFrame(data)

# Filter runs
if "type" in df.columns:
    df = df[df["type"] == "Run"]
elif "sport_type" in df.columns:
    df = df[df["sport_type"] == "Run"]

# Metrics
df["distance_km"] = df["distance"] / 1000
df["time_min"] = df["moving_time"] / 60
df = df[df["distance_km"] > 0]
df["pace"] = df["time_min"] / df["distance_km"]

df["start_date_local"] = pd.to_datetime(df["start_date_local"], utc=True)

# Sort
df = df.sort_values("start_date_local", ascending=False)

latest = df.iloc[0]

# =========================
# 📊 DASHBOARD
# =========================
col1, col2, col3 = st.columns(3)

col1.metric("Distance (km)", f"{latest['distance_km']:.2f}")
col2.metric("Pace", f"{latest['pace']:.2f} /km")
col3.metric("Run Type", "Easy")

st.caption(f"Latest run: {latest['start_date_local'].strftime('%Y-%m-%d')}")

# =========================
# 📈 CHART
# =========================
df_chart = df.sort_values("start_date_local")

fig = px.line(
    df_chart.tail(20),
    x="start_date_local",
    y="distance_km",
    title="Distance Trend"
)

st.plotly_chart(fig)

# =========================
# 🧠 TRAINING INTELLIGENCE
# =========================
today = pd.Timestamp.now(tz="UTC")

last_7 = df[df["start_date_local"] > (today - pd.Timedelta(days=7))]

runs_last_7 = len(last_7)
total_km_7 = last_7["distance_km"].sum()
avg_pace_7 = last_7["pace"].mean()

training_load = total_km_7 * runs_last_7

trend = "improving" if df["distance_km"].iloc[:5].mean() > df["distance_km"].iloc[5:10].mean() else "declining"

fatigue_status = "Fresh"
if runs_last_7 >= 5:
    fatigue_status = "Fatigued"
elif runs_last_7 >= 3:
    fatigue_status = "Moderate"

st.subheader("🧠 Training Intelligence")

colA, colB, colC = st.columns(3)

colA.metric("Training Load", int(training_load))
colB.metric("Fatigue", fatigue_status)

# =========================
# 🤖 AI COACH
# =========================
analysis_prompt = f"""
You are a professional running coach.

Here is my data:

- Runs last 7 days: {runs_last_7}
- Total distance: {total_km_7:.2f} km
- Average pace: {avg_pace_7:.2f}
- Latest run pace: {latest['pace']:.2f}
- Trend: {trend}
- Training load: {training_load}
- Fatigue: {fatigue_status}

Tell me:
1. Should I run today or rest?
2. What type of run?
3. Pace
4. Duration

Keep it short.
"""

try:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": analysis_prompt}]
    )

    ai_text = response.choices[0].message.content

    st.subheader("🤖 AI Coach Recommendation")
    st.success(ai_text)

except Exception as e:
    st.error("AI not working")
    st.write(e)

# =========================
# 📊 WEEKLY BAR
# =========================
df["week"] = df["start_date_local"].dt.to_period("W").astype(str)

weekly = df.groupby("week")["distance_km"].sum().reset_index()

fig2 = px.bar(weekly.tail(8), x="week", y="distance_km", title="Weekly Distance")
st.plotly_chart(fig2)

# =========================
# DEBUG
# =========================
with st.expander("Debug"):
    st.write(df.head())