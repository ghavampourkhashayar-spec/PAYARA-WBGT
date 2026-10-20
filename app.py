import streamlit as st
import requests
from datetime import datetime
import jdatetime

# ==========================================
# 1. تنظیمات اولیه صفحه و ظاهر
# ==========================================
st.set_page_config(page_title="PAYARA.ONE | WBGT Dashboard", page_icon="🌡️", layout="wide")

# CSS برای زیباسازی
st.markdown("""
    <style>
    .big-font { font-size:24px !important; font-weight: bold; }
    .wbgt-card { padding: 20px; border-radius: 15px; text-align: center; color: white; margin-bottom: 20px; box-shadow: 0 4px 8px rgba(0,0,0,0.2); }
    .metric-box { background-color: #f0f2f6; padding: 15px; border-radius: 10px; text-align: center; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. سایدبار (اطلاعات طراح)
# ==========================================
with st.sidebar:
    st.markdown("---")
    st.markdown("###  Developer")
    st.markdown("**Khashayar Ghavampour**")
    st.markdown("*Occupational Health Specialist*")
    st.markdown("*M.Sc. in Environmental Engineering*")
    st.markdown("*Company: Rahbarane Iman Paya*")
    st.caption("Version 1.0 | 2026")
    
    st.markdown("---")
    st.info("This application estimates the Wet-Bulb Globe Temperature (WBGT) for **Outdoor** industrial environments.")
    
    # دکمه سفارش ربات
    st.markdown("---")
    st.markdown("### 🤖 Need a Bot Version?")
    st.markdown("[Get the Custom Bot Version](https://payara.one)") # لینک سایت خود را اینجا جایگزین کنید

# ==========================================
# 3. هدر اصلی (لوگو و بنر)
# ==========================================
st.markdown("""
    <h1 style='text-align: center; color: #1e3c72; font-size: 40px; margin-bottom: 20px;'>
    Outdoor WBGT & Heat Stress Dashboard
    </h1>
""", unsafe_allow_html=True)

# نمایش بنر
st.image("banner.png", use_container_width =True)
st.divider()

# ==========================================
# 4. بخش ورودی‌ها
# ==========================================
st.subheader("1. Input Parameters")

col1, col2, col3 = st.columns(3)

with col1:
    CITIES = {
        "Abadan": {"lat": 30.3392, "lon": 48.3043},
        "Mahshahr": {"lat": 30.5589, "lon": 49.1981},
        "Bandar Abbas": {"lat": 27.1832, "lon": 56.2666},
        "Tehran": {"lat": 35.6892, "lon": 51.3890},
        "Isfahan": {"lat": 32.6546, "lon": 51.6680},
        "Manual Coordinates (Custom)": {"lat": None, "lon": None}
    }
    selected_city = st.selectbox("📍 Select Location:", list(CITIES.keys()))
    
    if selected_city == "Manual Coordinates (Custom)":
        lat = st.number_input("Latitude:", value=30.3392, format="%.4f")
        lon = st.number_input("Longitude:", value=48.3043, format="%.4f")
        location_name = "Custom Location"
    else:
        lat = CITIES[selected_city]["lat"]
        lon = CITIES[selected_city]["lon"]
        location_name = selected_city

with col2:
    data_source = st.radio("📊 Data Source:", ["Auto (Global Model)", "Manual Input"])
    time_option = st.radio("⏱️ Assessment Time:", ["Current Time", "Forecast (15:00 Today)"])

with col3:
    is_shade = st.checkbox("🌳 Working in the Shade")
    activity_level = st.selectbox("🏃 Activity Level:", ["Light", "Moderate", "Heavy"])

# ورود داده دستی
if data_source == "Manual Input":
    st.info("Please enter the weather data from your local meteorological station:")
    c1, c2, c3, c4 = st.columns(4)
    manual_ta = c1.number_input("Temperature (°C):", value=30.0)
    manual_rh = c2.number_input("Humidity (%):", value=50.0)
    manual_ws = c3.number_input("Wind Speed (m/s):", value=2.0)
    manual_sr = c4.number_input("Solar Radiation (kW/m²):", value=0.5)

st.divider()

# ==========================================
# 5. دکمه محاسبه و منطق اصلی
# ==========================================
if st.button("🚀 Calculate WBGT", type="primary", use_container_width=True):
    
    with st.spinner("Processing data..."):
        try:
            # --- دریافت داده ---
            if data_source == "Auto (Global Model)":
                url = "https://api.open-meteo.com/v1/forecast"
                params = {
                    "latitude": lat, "longitude": lon,
                    "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,shortwave_radiation,apparent_temperature,dew_point_2m,cloud_cover",
                    "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m,shortwave_radiation",
                    "wind_speed_unit": "ms", "timezone": "Asia/Tehran"
                }
                response = requests.get(url, params=params, timeout=10)
                res_data = response.json()
                
                if time_option == "Current Time":
                    data = res_data["current"]
                    ta, rh, ws = data["temperature_2m"], data["relative_humidity_2m"], data["wind_speed_10m"]
                    sr = 0.0 if is_shade else data["shortwave_radiation"] / 1000.0
                    measure_time = datetime.fromisoformat(data["time"])
                    extra_weather = data
                else:
                    times = res_data["hourly"]["time"]
                    target_index = next(i for i, t in enumerate(times) if "T15:00" in t)
                    ta = res_data["hourly"]["temperature_2m"][target_index]
                    rh = res_data["hourly"]["relative_humidity_2m"][target_index]
                    ws = res_data["hourly"]["wind_speed_10m"][target_index]
                    sr = 0.0 if is_shade else res_data["hourly"]["shortwave_radiation"][target_index] / 1000.0
                    measure_time = datetime.fromisoformat(times[target_index])
                    extra_weather = None
            else:
                ta, rh, ws, sr = manual_ta, manual_rh, manual_ws, manual_sr
                if is_shade: sr = 0.0
                measure_time = datetime.now()
                extra_weather = None

            # --- محاسبات ---
            wbgt = (0.718 * ta) + (0.0316 * rh) + (0.00321 * (ta * rh)) + (4.363 * sr) - (0.0502 * ws) - 3.623
            wbgt = round(wbgt, 2)
            
            # Heat Index با بررسی اعتبار
            if rh < 20:
                hi_text = "N/A (Humidity too low)"
            else:
                hi = -42.379 + 2.04901523 * ta + 10.14333127 * rh - 0.22475541 * ta * rh - 0.00683783 * ta**2 - 0.05481717 * rh**2 + 0.00122874 * ta**2 * rh + 0.00085282 * ta * rh**2 - 0.00000199 * ta**2 * rh**2
                hi_text = f"{round(hi, 2)} °C"

            # تعیین ریسک و توصیه
            if wbgt < 25:
                risk, color, action = "Safe", "#28a745", "No specific restrictions."
            elif 25 <= wbgt < 28:
                risk, color, action = "Caution", "#ffc107", "15 min rest per hour in shade."
            elif 28 <= wbgt < 31:
                risk, color, action = "High Stress", "#fd7e14", "30 min rest per hour in shade."
            else:
                risk, color, action = "Extreme Danger", "#dc3545", "45 min rest per hour in shade. Stop non-essential work."

            # تبدیل تاریخ
            shamsi_date = jdatetime.datetime.fromgregorian(datetime=measure_time)
            days = {0:"Monday", 1:"Tuesday", 2:"Wednesday", 3:"Thursday", 4:"Friday", 5:"Saturday", 6:"Sunday"}
            # استفاده از تاریخ میلادی در متن انگلیسی برای هماهنگی
            shamsi_str = f"{days[shamsi_date.weekday()]}, {shamsi_date.strftime('%Y/%m/%d')} - {shamsi_date.strftime('%H:%M')}"
            gregorian_str = measure_time.strftime("%Y-%m-%d %H:%M")

            # ==========================================
            # 6. نمایش خروجی
            # ==========================================
            st.success(f"Data processed successfully for **{location_name}**")
            
            # کارت اصلی
            text_color = "white" if color != "#ffc107" else "black"
            st.markdown(f"""
            <div class="wbgt-card" style="background-color: {color};">
                <h2 style="color: {text_color}; margin: 0;">Estimated Outdoor WBGT</h2>
                <h1 style="color: {text_color}; font-size: 70px; margin: 10px 0;">{wbgt} °C</h1>
                <h3 style="color: {text_color}; margin: 0;">Risk Level: {risk}</h3>
                <p style="color: {text_color}; margin-top: 15px; font-size: 18px;"><b>Recommendation:</b> {action}</p>
            </div>
            """, unsafe_allow_html=True)

            # اطلاعات زمان و Heat Index
            c_date, c_hi = st.columns(2)
            c_date.markdown(f"**📅 Date (Shamsi):** {shamsi_str}  \n*({gregorian_str})*")
            c_hi.markdown(f"**📊 Heat Index:** {hi_text}")

            st.divider()
            
            # شرایط جوی تکمیلی
            if extra_weather:
                st.subheader("Detailed Weather Conditions")
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"<div class='metric-box'><b>Air Temp</b><br><span class='big-font'>{ta} °C</span></div>", unsafe_allow_html=True)
                c2.markdown(f"<div class='metric-box'><b>Humidity</b><br><span class='big-font'>{rh} %</span></div>", unsafe_allow_html=True)
                c3.markdown(f"<div class='metric-box'><b>Wind Speed</b><br><span class='big-font'>{ws} m/s</span></div>", unsafe_allow_html=True)
                
                c4, c5, c6 = st.columns(3)
                c4.markdown(f"<div class='metric-box'><b>Solar Radiation</b><br><span class='big-font'>{sr} kW/m²</span></div>", unsafe_allow_html=True)
                c5.markdown(f"<div class='metric-box'><b>Dew Point</b><br><span class='big-font'>{extra_weather.get('dew_point_2m', 'N/A')} °C</span></div>", unsafe_allow_html=True)
                c6.markdown(f"<div class='metric-box'><b>Cloud Cover</b><br><span class='big-font'>{extra_weather.get('cloud_cover', 'N/A')} %</span></div>", unsafe_allow_html=True)

            # ==========================================
            # 7. خروجی و اشتراک‌گذاری
            # ==========================================
            st.divider()
            st.subheader("Export & Share")
            
            # دانلود CSV
            csv_data = f"Location,Date,WBGT,Risk,Recommendation\n{location_name},{shamsi_str},{wbgt},{risk},{action}"
            
            col_dl, col_copy = st.columns(2)
            with col_dl:
                st.download_button(
                    label="📥 Download Report (CSV)",
                    data=csv_data,
                    file_name=f"WBGT_Report_{location_name}.csv",
                    mime="text/csv",
                )
            
            # متن برای کپی (انگلیسی و عمومی)
            share_text = f"🌡️ WBGT Report ({location_name})\n📅 {shamsi_str}\nWBGT: {wbgt} °C\nRisk Level: {risk}\nRecommendation: {action}"
            with col_copy:
                st.code(share_text, language="text")
                st.caption("Copy the text above to share it on any messaging app.")

        except Exception as e:
            st.error(f"Error processing data: {e}")

# ==========================================
# 8. بخش About، راهنما و Disclaimer
# ==========================================
st.divider()

col_guide, col_about = st.columns(2)

with col_guide:
    with st.expander("📖 Quick User Guide"):
        st.markdown("""
        1. **Select Location:** Choose a city or enter custom coordinates.
        2. **Data Source:** Keep it on "Auto" for live weather data.
        3. **Conditions:** Check the "Shade" box if the worker is not under direct sunlight.
        4. **Calculate:** Click the calculate button to see the WBGT and safety recommendations.
        5. **Export:** Use the download or copy buttons to save or share the report.
        """)

with col_about:
    with st.expander("ℹ️ About & Disclaimer"):
        st.markdown("""
        **About this tool:**
        This application estimates the Outdoor Wet-Bulb Globe Temperature (WBGT) using the estimation method based on the standard approach utilized by the Japan Ministry of the Environment for heat stress assessment. It is designed for outdoor industrial environments and provides a work/rest recommendation based on the calculated WBGT.
        
        **Disclaimer:**
        This WBGT value is an estimation based on meteorological data. It is intended for informational and planning purposes only and does not replace on-site measurement with calibrated WBGT instruments. This tool is not designed for medical diagnosis, legal judgment, or regulatory compliance purposes. Employers and safety managers remain responsible for conducting site-specific risk assessments.
        """)
