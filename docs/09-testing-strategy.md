# Testing Strategy

## 1. اهداف

- جلوگیری از از‌دست‌رفتن کار طولانی پس از خطا
- کشف سریع شکست adapterها در اثر تغییر UI سرویس‌ها
- تضمین lineage، مقیاس FBX و صحت state transition
- کاهش وابستگی تست روزانه به سرویس‌های خارجی و حساب واقعی

## 2. هرم تست

### Unit Tests — بیشترین تعداد

- state machine و transitionهای مجاز/غیرمجاز
- retry policy و backoff
- building code allocation
- circle/footprint intersection
- height calculation strategies
- reference scoring
- invalidation تأییدها پس از تغییر upstream
- crop template و image validation
- scale factor و tolerance مدل
- redaction و secret handling

### Integration Tests

- repository و migration روی SQLite واقعی موقت
- atomic artifact write و recovery
- application use case + fake provider
- API + database + worker queue
- Telegram dispatcher با mock HTTP server
- Blender headless با fixtureهای کوچک
- Playwright adapter با صفحات HTML محلی شبیه‌سازی‌شده

### Contract Tests

برای هر provider مجموعه‌ای از snapshot/fixture نگهداری می‌شود:

- تشخیص logged-in/logged-out/captcha
- upload mapping پنج جهت
- شروع job و خواندن progress
- download event
- extraction metadata دوربین

Contract test روزانه اختیاری با سایت واقعی، حساب تست و داده کم اجرا می‌شود و از test suite عادی جداست.

### End-to-End Tests

سناریوی fake-provider کامل:

1. ایجاد پروژه
2. detection fixture
3. Map Approval
4. reference collection fixture
5. Reference Approval
6. generated sheet fixture و crop
7. View Approval
8. model fixture
9. Blender validation/scale
10. completion و report

سناریوی live smoke محدود پیش از release با یک ساختمان انجام می‌شود.

## 3. تست‌های Recovery

در هر boundary مهم، process عمداً terminate می‌شود:

- وسط download تصویر
- پس از ثبت attempt و پیش از artifact
- پس از فایل نهایی و پیش از DB commit
- هنگام انتظار Hunyuan
- وسط Blender export
- هنگام ارسال Telegram

پس از restart باید duplicate کنترل شود، فایل partial پاک/قرنطینه شود و pipeline از checkpoint درست ادامه یابد.

## 4. تست رابط کاربری

- pytest-qt برای view-model و interactionها
- تست ویرایش footprint، height و batch approval
- نمایش واضح `NeedsReview` و error reason
- جلوگیری از تأیید ناقص پنج نما
- UI responsiveness هنگام worker فعال
- تست رزولوشن رایج مانیتور ویندوز و scaling 125/150 درصد

## 5. Golden Dataset

یک مجموعه داخلی و versioned از ۵ تا ۱۰ محدوده تهران ایجاد شود که شامل موارد زیر باشد:

- ساختمان کوتاه و بلند
- footprint ساده و پیچیده
- سایه واضح و نامشخص
- خیابان باریک و occlusion زیاد
- تصویر واقعی موجود و ناموجود
- ساختمان در مرز شعاع

برای هر نمونه ground truth تقریبی footprint، طبقات و ارتفاع توسط تیم ثبت می‌شود. تصاویر دارای محدودیت مجوز نباید داخل repository عمومی قرار گیرند؛ manifest مسیر secure dataset را نگه می‌دارد.

## 6. معیارهای کیفیت الگوریتمی

- Footprint detection: IoU و نرخ ساختمان missed/extra در سطح پروژه
- Height: MAE بر حسب طبقه و متر
- Reference assignment: top-1/top-3 accuracy با تأیید انسانی
- View crop: وجود و ابعاد صحیح هر پنج تصویر
- Model validation: import success و dimension tolerance

هدف اولیه ارتفاع: خطا حداکثر یک طبقه در اکثر نمونه‌های قابل‌اندازه‌گیری. threshold دقیق detection پس از baseline golden dataset تعیین می‌شود.

## 7. Performance و Soak

- اجرای ۲۴ ساعته با fake provider و صدها transition
- پروژه ۲۰ ساختمانی با artifactهای حجیم
- کنترل رشد RAM مرورگر و worker
- فضای دیسک کم و رفتار graceful
- latency UI زیر بار worker

## 8. Security Tests

- scan log/report/project export برای Telegram token، cookie و authorization header
- bindشدن API فقط روی loopback
- path traversal در upload و artifact access
- MIME/extension mismatch
- فایل FBX خراب یا بسیار بزرگ
- محدودیت path و filename ویندوز

## 9. Release Gate

- unit و integration سبز
- migration upgrade از نسخه قبلی و backup/restore موفق
- fake-provider E2E موفق
- live smoke برای providerهای فعال موفق یا risk sign-off ثبت‌شده
- Blender fixtureها روی ماشین هدف موفق
- Telegram test موفق یا feature به‌صورت واضح degraded اعلام شود
- هیچ secret در artifact release وجود نداشته باشد

