# راهنمای اپراتور Near Project Environment

## شروع روزانه

1. Chrome اختصاصی را باز کنید و Login بودن Google Maps، ChatGPT و Hunyuan را بررسی کنید.
2. Hunyuan را در یک Tab مستقل باز نگه دارید. دانلود FBX در نسخه MVP دستی است.
3. برنامه را اجرا کنید. Preflight باید Database، Disk، Browser Profile و Blender را بررسی کند.
4. اگر Worker در وضعیت Stopped یا Stale است، برنامه را یک‌بار ببندید و دوباره اجرا کنید.

## نصب و ارتقا

1. ZIP رسمی Release را Extract کنید؛ فایل‌ها را جداگانه جابه‌جا نکنید.
2. `install.ps1` را اجرا کنید. Installer پیش از نصب checksum همه فایل‌ها را کنترل می‌کند.
3. نسخه قبلی موقتاً به `.previous` منتقل می‌شود.
4. Upgrade قبل از migration یک SQLite backup معتبر در `<DATA_ROOT>/backups` می‌سازد.
5. اگر prerequisite یا migration شکست بخورد، فایل‌های نسخه قبلی خودکار برگردانده می‌شوند.

## اجرای پروژه

پس از Map approval، reference approval و five-view approval، تصاویر به Hunyuan ارسال می‌شوند. وقتی مدل آماده شد، FBX را دستی دانلود و از گزینه Register Download وارد کنید. ساختمان NeedsReview نباید اجرای سایر ساختمان‌ها را متوقف کند.

## بازیابی و ادامه

- پس از قطع برق یا بسته‌شدن برنامه، همان Project را باز و Resume کنید.
- Jobهای `running` قدیمی با Recovery به آخرین Stage امن برمی‌گردند.
- پس از دو شکست خودکار، ساختمان NeedsReview می‌شود و ادامه پروژه‌های دیگر مجاز است.
- Logout یا CAPTCHA نیازمند Login انسانی است؛ Credential یا Cookie را در پیام یا گزارش قرار ندهید.

## مسیر دستی جایگزین

اگر کنترل Hunyuan شکست خورد، پنج فایل تأییدشده را از پوشه `generated/approved` دستی Upload کنید، FBX را دانلود و با Building Code درست Register کنید. Mapping جهت‌ها را تغییر ندهید.

## گزارش عیب‌یابی

`NearProjectEnvironment.exe --component diagnostics` یک ZIP پاک‌سازی‌شده می‌سازد. فقط همین ZIP را برای توسعه‌دهنده ارسال کنید. Browser profile، `.env`، Database کامل و Token تلگرام را ارسال نکنید.

## Rollback

اگر Upgrade ناموفق باشد Installer خودکار نسخه قبلی را برمی‌گرداند. برای بازگرداندن Database، فقط از Backup داخل `<DATA_ROOT>/backups` و فرمان رسمی Restore استفاده کنید. فایل Database فعال را هنگام اجرای برنامه Copy نکنید.

## پایان پروژه

گزارش HTML، `overview/buildings.csv`، پوشه‌های B001…، manifest و checksum را بازبینی کنید. موارد Missing و NeedsReview باید در تحویل و گزارش نهایی صریح باقی بمانند.
