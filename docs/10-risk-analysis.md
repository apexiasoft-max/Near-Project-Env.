# Risk Analysis

## روش امتیازدهی

احتمال و اثر از ۱ تا ۵ امتیاز دارند. امتیاز ریسک برابر `Probability × Impact` است:

- ۱ تا ۵: پایین
- ۶ تا ۱۲: متوسط
- ۱۵ تا ۲۵: بالا

## رجیستر ریسک MVP

| ریسک | احتمال | اثر | امتیاز | راهکار اصلی |
|---|---:|---:|---:|---|
| تغییر UI ChatGPT یا Hunyuan | 5 | 4 | 20 | adapter مجزا، selector version، contract smoke، manual fallback |
| کپچا یا logout | 4 | 3 | 12 | تشخیص سریع، pause stage، Telegram، profile اختصاصی |
| محدودیت/عدم دسترسی Google یا نشان | 4 | 5 | 20 | spike اولیه، provider abstraction، استخر دستی و upload انسانی |
| محدودیت شرایط استفاده یا مجوز داده | 3 | 5 | 15 | بررسی حقوقی/قراردادی پیش از production، حداقل‌سازی ذخیره و مصرف داخلی |
| انتساب تصویر به ساختمان اشتباه | 4 | 4 | 16 | هندسه camera/footprint، confidence، تأیید دوم، نمایش source context |
| نبود تصویر واقعی یا مرجع دستی | 4 | 3 | 12 | `MissingReference`، ادامه سایر موارد، اعلان و upload دستی |
| تخمین ارتفاع بیش از یک طبقه خطا | 3 | 4 | 12 | چند estimator، range/confidence، override و golden dataset |
| سایه نامعتبر/زمین شیب‌دار | 4 | 3 | 12 | quality gate، عدم نمایش قطعیت کاذب، fallback به طبقات/مرجع |
| ناسازگاری پنج نمای تولیدی | 4 | 4 | 16 | prompt/template ثابت، checks خودکار، تأیید سوم، regenerate جهت خاص |
| شکست Detection به‌علت نمای سفید/طوسی یا پس‌زمینه کم‌کنتراست | 4 | 4 | 16 | قرارداد prompt نسخه‌دار: تکسچر و رنگ واقعی نما، پس‌زمینه خاکستری تیره RGB 72/76/82، کنترل اندازه سوژه و Approval اجباری |
| خروجی خراب یا بد Hunyuan | 4 | 4 | 16 | validation، دو retry، نگهداری raw artifact، NeedsReview |
| FBX scale یا axis اشتباه | 3 | 5 | 15 | Blender pipeline ثابت، unit/axis contract، fixture tests |
| crash یا restart در کار طولانی | 3 | 5 | 15 | persistent queue، checkpoint، atomic file، recovery tests |
| پرشدن دیسک | 3 | 4 | 12 | preflight capacity، quota/retention، توقف امن پیش از write |
| نشت token/cookie در log یا trace | 2 | 5 | 10 | Credential Manager، redaction، security scan، retention کوتاه |
| Telegram در شبکه در دسترس نیست | 4 | 2 | 8 | test در preflight، proxy قابل‌تنظیم، اعلان داخل UI، non-blocking |
| اجرای هم‌زمان عملیات روی یک session | 3 | 3 | 9 | serialization provider jobs، lock و single browser owner |
| تغییر schema یا از‌دست‌رفتن DB | 2 | 5 | 10 | migration test، backup قبل upgrade، WAL و integrity check |

## ریسک‌های نیازمند Spike پیش از ساخت کامل

### 1. Source Acquisition

باید با چند مختصات واقعی تهران بررسی شود که چه metadata و تصاویر قابل‌دسترسی است، انتساب زاویه دید تا چه حد ممکن است و روش استفاده با قواعد سرویس‌ها سازگار است. این بالاترین ریسک feasibility است.

### 2. Web Automation

یک مسیر باریک end-to-end برای یک ساختمان ساخته شود: دریافت reference آماده، تولید شیت در ChatGPT، برش، upload پنج تصویر به Hunyuan و download. زمان، captcha، selector stability و download behavior ثبت شود.

### 3. FBX Pipeline

چند مدل واقعی Hunyuan در Blender headless import، اندازه‌گیری، scale و export شوند و سپس در Blender و 3ds Max بازبینی شوند. unit، axis و transform policy قبل از توسعه گسترده تثبیت شود.

### 4. Footprint and Height Baseline

پنج محدوده نمونه با ground truth انسانی انتخاب و baseline دقت detection و height ثبت شود. بدون baseline، معیار «بهترین تخمین» قابل‌اندازه‌گیری نیست.

## برنامه کاهش ریسک مرحله‌ای

### Gate A — Feasibility

- source acquisition برای تهران اثبات شود.
- web automation یک ساختمان کامل شود.
- FBX scale round-trip موفق باشد.

### Gate B — Reliable Single Building

- سه approval، دو retry، crash recovery و Telegram برای یک ساختمان کامل شود.

### Gate C — Typical Project

- پروژه ۱۰ تا ۲۰ ساختمانی اجرا و bottleneck، disk usage و دخالت انسانی اندازه‌گیری شود.

### Gate D — Internal Pilot

- دو پروژه واقعی توسط تیم و بدون همراهی روزانه توسعه‌دهنده اجرا شود.

## برنامه جایگزین

- اگر کنترل ChatGPT پایدار نبود: adapter دستی upload/download یا API رسمی در آینده.
- اگر Hunyuan automation پایدار نبود: export بسته پنج‌تصویری آماده upload و import دستی FBX.
- اگر source acquisition ممکن نبود: upload تصاویر توسط کاربر و حفظ pipeline از Reference Approval به بعد.
- اگر Telegram مسدود بود: notification center داخل برنامه و proxy اختیاری؛ pipeline ادامه می‌یابد.

## ریسک پذیرفته‌شده MVP

کنترل رابط وب ذاتاً شکننده است. این ریسک برای نسخه داخلی پذیرفته می‌شود، مشروط بر اینکه adapterها جدا، failureها قابل‌تشخیص، و مسیر دستی برای ادامه کار موجود باشد.
