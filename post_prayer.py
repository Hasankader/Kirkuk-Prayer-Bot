import requests
import pandas as pd
import datetime
import pytz
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

# 1. معلومات صفحتك (الرمز الدائم)
PAGE_ID = '261762917029378'
ACCESS_TOKEN = 'EABAcvzlSGwoBQ238zdkpH7rfcn1ZC0zAhc7vmZA2ngn9IWNS3WQrbtkj9DXYuFWh1b0HNwIYvodDAGY0T0LpHFIrk1xuMw8ChSE5mkjGw3dbgnGk69QPE2nn6rb7ltY9bo5MZC9E2QnnxFZC6wvO1Sb7v9C2vZCaNVPUmkHkmSQQrppXXejIxUMpdNv5wmXyZBy8snFvUrywlURfqSDQvsNJYZD'

ARABIC_DAYS = {
    'Sunday': 'الأحد', 'Monday': 'الاثنين', 'Tuesday': 'الثلاثاء',
    'Wednesday': 'الأربعاء', 'Thursday': 'الخميس', 'Friday': 'الجمعة', 'Saturday': 'السبت'
}

# 2. ضبط توقيت العراق (مهم جداً لسيرفرات گيت هاب)
iraq_tz = pytz.timezone('Asia/Baghdad')
now = datetime.datetime.now(iraq_tz)
today_date = now.date()
tomorrow_date = today_date + datetime.timedelta(days=1)

def fix_arabic_text(text):
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

def check_if_posted(identifier, hours=12):
    """دالة ذكية تفحص صفحتك بالفيسبوك لتتأكد هل تم النشر مسبقاً أم لا"""
    url = f"https://graph.facebook.com/v19.0/{PAGE_ID}/feed"
    params = {'access_token': ACCESS_TOKEN, 'limit': 10}
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if 'data' in data:
            for post in data['data']:
                message = post.get('message', '')
                created_time_str = post.get('created_time', '')
                if not created_time_str: continue
                
                post_time_utc = datetime.datetime.strptime(created_time_str, "%Y-%m-%dT%H:%M:%S+0000")
                post_time_utc = pytz.utc.localize(post_time_utc)
                time_diff = now - post_time_utc
                
                # إذا كان المنشور نازل خلال الـ 12 ساعة الماضية ويحتوي على نفس الهاشتاگ
                if time_diff.total_seconds() < (hours * 3600) and identifier in message:
                    return True
    except Exception as e:
        pass
    return False

def post_to_facebook(caption, image_path):
    url = f"https://graph.facebook.com/v19.0/{PAGE_ID}/photos"
    payload = {'message': caption, 'access_token': ACCESS_TOKEN}
    try:
        with open(image_path, 'rb') as img:
            files = {'source': img}
            response = requests.post(url, data=payload, files=files)
            if response.status_code == 200:
                print(f" تم النشر بنجاح على الفيسبوك!")
            else:
                print(f" خطأ من فيسبوك: {response.json()}")
    except Exception as e:
        print(f" خطأ بالنشر: {e}")

def create_schedule_image(date_str, fajr, sunrise, dhuhr, asr, maghrib, isha):
    template_path = 'template.jpg' # مسار مجرد (يصلح للسيرفرات)
    output_path = 'ready_schedule.jpg'
    try:
        img = Image.open(template_path)
        draw = ImageDraw.Draw(img)
        try:
            # يجب رفع خط arial.ttf مع الملفات على گيت هاب
            font = ImageFont.truetype("arial.ttf", 45)
        except:
            font = ImageFont.load_default()

        color = (255, 255, 255) 
        x = 280 
        draw.text((x - 150, 250), date_str, font=font, fill=color)
        draw.text((x, 350), fajr, font=font, fill=color)
        draw.text((x, 450), sunrise, font=font, fill=color)
        draw.text((x, 550), dhuhr, font=font, fill=color)
        draw.text((x, 650), asr, font=font, fill=color)
        draw.text((x, 750), maghrib, font=font, fill=color)
        draw.text((x, 850), isha, font=font, fill=color)
        img.save(output_path)
        return output_path
    except Exception as e:
        print(f" خطأ برسم الصورة: {e}")
        return None

print(f"🚀 بوت كركوك بدأ الفحص في الوقت: {now.strftime('%I:%M %p')}")

try:
    file_path = 'kirkuk_prayers.xlsx'
    df = pd.read_excel(file_path)
    df.columns = [str(c).strip() for c in df.columns]
    date_col = next((c for c in df.columns if 'date' in c.lower()), 'Date')
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce').dt.date
    
    today_data = df[df[date_col] == today_date]
    tomorrow_data = df[df[date_col] == tomorrow_date]

    def clean_t(val): return str(val).split(' ')[-1][:5]

    # =========================================================
    # 1. نشر جدول يوم غد (الساعة 9:00 مساءً)
    # =========================================================
    target_time_str = "09:00 PM"
    target_time_obj = datetime.datetime.strptime(target_time_str, "%I:%M %p").time()
    target_dt = iraq_tz.localize(datetime.datetime.combine(today_date, target_time_obj))

    # إذا صارت الساعة 9 أو عبرت بشوية (ضمن ساعتين)
    if now >= target_dt and (now - target_dt).total_seconds() < 7200:
        if not check_if_posted("ليوم غدٍ"):
            if not tomorrow_data.empty:
                t = tomorrow_data.iloc[0]
                day_ar = ARABIC_DAYS.get(tomorrow_date.strftime('%A'), '')
                raw_date_text = f"{day_ar} {tomorrow_date}"
                fixed_date_text = fix_arabic_text(raw_date_text)
                
                print(" جاري تصميم صورة جدول الغد...")
                img_path = create_schedule_image(
                    fixed_date_text, clean_t(t['Fajr']), clean_t(t['Sunrise']), 
                    clean_t(t['Dhuhr']), clean_t(t['Asr']), clean_t(t['Maghrib']), clean_t(t['Isha'])
                )
                
                if img_path:
                    caption = f" مواقيت الصلاة ليوم غدٍ {day_ar} لمدينة كركوك الحبيبة.\nتقبل الله طاعاتكم🌹"
                    print(" حان وقت نشر الجدول!")
                    post_to_facebook(caption, img_path)
            else:
                print(" لم أجد بيانات لباجر بملف الإكسل!")

    # =========================================================
    # 2. نشر الأذان المفرد
    # =========================================================
    if not today_data.empty:
        times = today_data.iloc[0]
        prayers = [
            {"n": "الفجر", "c": "Fajr", "ap": "AM", "img": "fajr.jpg"},
            {"n": "الظهر", "c": "Dhuhr", "ap": "AM" if clean_t(times['Dhuhr']).startswith("11") else "PM", "img": "dhuhr.jpg"},
            {"n": "العصر", "c": "Asr", "ap": "PM", "img": "asr.jpg"},
            {"n": "المغرب", "c": "Maghrib", "ap": "PM", "img": "maghrib.jpg"},
            {"n": "العشاء", "c": "Isha", "ap": "PM", "img": "isha.jpg"}
        ]

        for p in prayers:
            prayer_time_str = f"{clean_t(times[p['c']])} {p['ap']}"
            prayer_time_obj = datetime.datetime.strptime(prayer_time_str, "%I:%M %p").time()
            prayer_dt = iraq_tz.localize(datetime.datetime.combine(today_date, prayer_time_obj))
            
            # إذا صار وقت الأذان (أو عبر بشوية ضمن ساعة واحدة)
            if now >= prayer_dt and (now - prayer_dt).total_seconds() < 3600:
                identifier = f"#اذان_{p['n']}"
                if not check_if_posted(identifier):
                    print(f" حان موعد أذان {p['n']}! جاري النشر...")
                    post_to_facebook(f" موعد أذان {p['n']}\n{clean_t(times[p['c']])}\n{identifier}", p['img'])

except Exception as e:
    print(f" خطأ: {e}")