# TripTrend Ver 1.3 — Deployment Preparation

هذه الحزمة هي نسخة تطويرية آمنة لربط TripTrend بقاعدة Google Sheets واستيراد ملف أسعار يومي متعدد التبويبات.

## الملفات الأساسية

- `hotel_analytics_app_v14.py`: نسخة التطبيق التطويرية.
- `triptrend_data_engine.py`: قراءة Excel متعدد Tabs وتوحيد الهيدرات والتواريخ والأسعار.
- `google_sheets_adapter.py`: قراءة وكتابة Google Sheets عبر Service Account من Secrets.
- `triptrend_sheets_config.py`: تحويل Tabs الإعلانات والعروض والبلوجرز والأفلييت والمستخدمين إلى إعدادات التطبيق.
- `requirements_triptrend_v14.txt`: حزم التشغيل.
- `TripTrend_GoogleSheets_Master_Template_v3_Examples.xlsx`: قالب Google Sheets متعدد Tabs مع أمثلة.

## متغيرات التشغيل

يجب وضعها في Streamlit Secrets، وليس في GitHub:

```toml
TRIPTREND_SPREADSHEET_ID = "1ywIUDJkKqVMA0_yBtcNmGgRMbyh1kAEC"
GOOGLE_SERVICE_ACCOUNT_JSON = "{...service account JSON...}"
```

شارك ملف Google Sheets الرئيسي مع بريد `client_email` الموجود داخل بيانات حساب الخدمة بصلاحية Editor. لا ترفع ملف JSON إلى GitHub.

## ملف الأسعار اليومي

يمكن رفع ملف واحد مثل:

`TripTrend_Daily_2026-08-29.xlsx`

ويحتوي على Tab لكل مدينة، مثل `Paris`, `London`, `NewYork`, `Switzerland`, `Dubai`. يحتفظ كل Tab بهيدر Trivago الأصلي. يعالج المحرك اختلافات مثل `Distance` و`Distance From places` و`Place2` و`place2` تلقائياً.

## اختبار تم بنجاح

على الملف الحقيقي المرفق تم تجهيز 1,228 سجل سعر و417 فندقاً فريداً. لم توجد أسعار Best_Price مفقودة أو صفرية، ولم توجد Record_Hash مكررة، وتم استنتاج تاريخ الوصول من أيام الأسبوع.

## قبل النشر العام

يجب اختبار الكتابة المحدودة في `Import_Log`، ثم اختبار استيراد مدينة واحدة، ثم استيراد كل المدن، ثم اختبار جميع صفحات Streamlit. لا تستخدم النسخة الحالية كنشر عام قبل اكتمال هذه الاختبارات.
