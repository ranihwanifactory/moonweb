import math
import datetime
import calendar
import streamlit as st
from PIL import Image, ImageDraw
import numpy as np

# ---------------------------------------------------------
# 1. 페이지 기본 설정
# ---------------------------------------------------------
st.set_page_config(
    page_title="달의 위상 & 출몰 시뮬레이터",
    page_icon="🌕",
    layout="wide"
)

st.title("🌕 달의 위상 & 출몰 시뮬레이터")
st.write("달의 일출/일몰, 월출/월몰 시간과 달 위상 변화 및 월간 달력을 한눈에 확인하세요.")

SYNODIC_MONTH = 29.53058867  # 삭망월 주기 (일)

# ---------------------------------------------------------
# 2. 천문학 계산 함수 (월령 및 위상)
# ---------------------------------------------------------
def get_moon_phase_info(target_date):
    known_new_moon = datetime.datetime(2000, 1, 6, 18, 14, 0, tzinfo=datetime.timezone.utc)
    
    if isinstance(target_date, datetime.date) and not isinstance(target_date, datetime.datetime):
        target_dt = datetime.datetime.combine(target_date, datetime.time(12, 0), tzinfo=datetime.timezone.utc)
    else:
        target_dt = target_date

    diff_days = (target_dt - known_new_moon).total_seconds() / 86400.0
    moon_age = diff_days % SYNODIC_MONTH
    phase_angle = (moon_age / SYNODIC_MONTH) * 2 * math.pi
    illumination = (1 - math.cos(phase_angle)) / 2 * 100

    if moon_age < 1.84566 or moon_age >= 27.68493:
        phase_name = "삭 (New Moon)"
        emoji = "🌑"
    elif moon_age < 5.53699:
        phase_name = "초승달 (Waxing Crescent)"
        emoji = "🌒"
    elif moon_age < 9.22831:
        phase_name = "상현달 (First Quarter)"
        emoji = "🌓"
    elif moon_age < 12.91963:
        phase_name = "차오름달 (Waxing Gibbous)"
        emoji = "🌔"
    elif moon_age < 16.61096:
        phase_name = "보름달 (Full Moon)"
        emoji = "🌕"
    elif moon_age < 20.30228:
        phase_name = "이그러짐달 (Waning Gibbous)"
        emoji = "🌖"
    elif moon_age < 23.99361:
        phase_name = "하현달 (Third Quarter)"
        emoji = "🌗"
    else:
        phase_name = "그믐달 (Waning Crescent)"
        emoji = "🌘"

    return moon_age, illumination, phase_angle, phase_name, emoji

# ---------------------------------------------------------
# 3. 일출/일몰 & 월출/월몰 약식 계산 함수 (순수 파이썬 수학 연산)
# ---------------------------------------------------------
def get_approx_sun_moon_riseset(target_date, moon_age):
    day_of_year = target_date.timetuple().tm_yday
    
    declination = 0.409 * math.sin(2 * math.pi * (day_of_year - 80) / 365)
    lat_rad = math.radians(37.5665)  # 서울 관측 기준
    
    try:
        hour_angle = math.acos(-math.tan(lat_rad) * math.tan(declination))
        sun_hours = math.degrees(hour_angle) / 15.0
    except ValueError:
        sun_hours = 6.0

    sunrise_dt = datetime.time(int(12 - sun_hours), int(((12 - sun_hours) % 1) * 60))
    sunset_dt = datetime.time(int(12 + sun_hours), int(((12 + sun_hours) % 1) * 60))

    moon_delay_hours = moon_age * (24.0 / SYNODIC_MONTH)
    
    moon_rise_hour = (6.0 + moon_delay_hours) % 24
    moon_set_hour = (18.0 + moon_delay_hours) % 24

    moon_rise_str = f"{int(moon_rise_hour):02d}:{int((moon_rise_hour % 1) * 60):02d}"
    moon_set_str = f"{int(moon_set_hour):02d}:{int((moon_set_hour % 1) * 60):02d}"

    return sunrise_dt.strftime("%H:%M"), sunset_dt.strftime("%H:%M"), moon_rise_str, moon_set_str

# ---------------------------------------------------------
# 4. 이미지 렌더링 함수 (moon.png + 그림자 마스크)
# ---------------------------------------------------------
def render_moon_phase(image_path, phase_angle):
    try:
        base_img = Image.open(image_path).convert("RGBA")
    except Exception:
        base_img = Image.new("RGBA", (400, 400), (200, 200, 200, 255))
        draw = ImageDraw.Draw(base_img)
        draw.ellipse((10, 10, 390, 390), fill=(180, 180, 180, 255))

    width, height = base_img.size
    radius = min(width, height) / 2.0
    center_x, center_y = width / 2.0, height / 2.0

    y, x = np.ogrid[:height, :width]
    nx = (x - center_x) / radius
    ny = (y - center_y) / radius
    dist_sq = nx**2 + ny**2

    moon_mask = dist_sq <= 1.0
    nz = np.sqrt(np.maximum(0, 1.0 - dist_sq))

    sun_x = -np.sin(phase_angle)
    sun_z = -np.cos(phase_angle)

    dot_product = nx * sun_x + nz * sun_z
    shadow_map = np.clip((dot_product + 0.1) / 0.2, 0.12, 1.0)
    shadow_map = np.where(moon_mask, shadow_map, 0.0)

    img_np = np.array(base_img).astype(float)
    for c in range(3):
        img_np[:, :, c] *= shadow_map
    img_np[:, :, 3] = np.where(moon_mask, img_np[:, :, 3], 0)

    return Image.fromarray(np.uint8(img_np))

# ---------------------------------------------------------
# 5. 사이드바 제어
# ---------------------------------------------------------
st.sidebar.header("🗓️ 날짜 설정")

selected_date = st.sidebar.date_input("기준 날짜 선택", datetime.date.today())
day_offset = st.sidebar.slider("날짜 미세 조정 (+/- 일)", -30, 30, 0)
target_date = selected_date + datetime.timedelta(days=day_offset)

# ---------------------------------------------------------
# 6. 메인 화면 렌더링
# ---------------------------------------------------------
moon_age, illumination, phase_angle, phase_name, emoji = get_moon_phase_info(target_date)
sun_rise, sun_set, moon_rise, moon_set = get_approx_sun_moon_riseset(target_date, moon_age)

col_img, col_info = st.columns([1, 1])

with col_img:
    st.subheader(f"📅 {target_date.strftime('%Y년 %m월 %d일')}")
    st.image(
        render_moon_phase("moon.png", phase_angle),
        caption=f"달 위상: {phase_name}",
        use_container_width=True
    )

with col_info:
    st.subheader("📊 위상 & 출몰 시간")
    
    m1, m2 = st.columns(2)
    m1.metric("🌅 일출 시간 (추정)", sun_rise)
    m2.metric("🌇 일몰 시간 (추정)", sun_set)
    
    m3, m4 = st.columns(2)
    m3.metric("🌕 월출 시간 (추정)", moon_rise)
    m4.metric("🌘 월몰 시간 (추정)", moon_set)
    
    st.markdown("---")
    st.metric(label="달의 위상", value=f"{emoji} {phase_name}")
    st.metric(label="월령 (Moon Age)", value=f"{moon_age:.2f} 일 / {SYNODIC_MONTH:.2f} 일")
    st.metric(label="표면 밝기 (Illumination)", value=f"{illumination:.1f} %")

st.markdown("---")

# ---------------------------------------------------------
# 7. 하단: 월간 달 위상 달력 (Calendar View)
# ---------------------------------------------------------
st.subheader(f"📅 {target_date.year}년 {target_date.month}월 달 위상 달력")

year = target_date.year
month = target_date.month

cal = calendar.monthcalendar(year, month)
days_of_week = ["월", "화", "수", "목", "금", "토", "일"]

cols = st.columns(7)
for i, day_name in enumerate(days_of_week):
    cols[i].markdown(f"**<center>{day_name}</center>**", unsafe_allow_html=True)

for week in cal:
    cols = st.columns(7)
    for i, day in enumerate(week):
        if day == 0:
            cols[i].write("")
        else:
            cur_date = datetime.date(year, month, day)
            m_age, m_illum, _, _, m_emoji = get_moon_phase_info(cur_date)
            
            if cur_date == target_date:
                border_style = "border: 2px solid #FF4B4B; background-color: rgba(255, 75, 75, 0.1);"
            else:
                border_style = "border: 1px solid #444;"
                
            cols[i].markdown(
                f"""
                <div style="{border_style} border-radius: 8px; padding: 6px; text-align: center;">
                    <div style="font-size: 14px; font-weight: bold;">{day}일</div>
                    <div style="font-size: 24px; margin: 2px 0;">{m_emoji}</div>
                    <div style="font-size: 10px; color: #888;">{m_illum:.0f}%</div>
                </div>
                """,
                unsafe_allow_html=True
            )