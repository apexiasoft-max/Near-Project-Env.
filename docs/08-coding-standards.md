# Coding Standards

## 1. اصول

- کد برای recovery و نگهداری نوشته می‌شود، نه فقط happy path.
- domain logic از UI، database و browser مستقل است.
- side effectها صریح و پشت interface هستند.
- هر عملیات خارجی قابل‌ردیابی، timeoutدار و cancellation-aware است.
- داده تأییدشده immutable یا versioned است.

## 2. Python

- Python 3.12 و type hint برای تمام APIهای عمومی.
- `mypy --strict` برای domain و application؛ استثناهای محدود مستند شوند.
- format با Black و lint/import با Ruff.
- طول خط 100 کاراکتر.
- `pathlib.Path` به‌جای string path.
- زمان داخلی timezone-aware و UTC.
- پول/فاصله و مختصات با value object؛ از float خام در domain boundary پرهیز شود.
- Pydantic برای transport/config؛ dataclass یا کلاس domain برای منطق دامنه.

## 3. نام‌گذاری

- module/function/variable: `snake_case`
- class/protocol: `PascalCase`
- constant: `UPPER_SNAKE_CASE`
- command: فعل امری مانند `GenerateBuildingViews`
- event: گذشته مانند `BuildingViewsGenerated`
- error code: `UPPER_SNAKE_CASE`
- boolean با `is/has/can/should` شروع شود.

## 4. معماری و dependency

- Domain فقط استاندارد لایبرری و dependencyهای صریح مجاز را import می‌کند.
- Infrastructure interfaceهای `application.ports` را implement می‌کند.
- route مستقیماً ORM query یا Playwright call نمی‌زند.
- UI فقط local API/client abstraction را صدا می‌زند.
- adapterهای provider هیچ state transition دامنه‌ای انجام نمی‌دهند.

## 5. خطا و retry

خطاها دسته‌بندی شوند:

- `TransientError`: شبکه، timeout، download موقت
- `HumanInterventionRequired`: کپچا، logout، نبود مرجع
- `ValidationError`: artifact نامعتبر
- `ConfigurationError`: مسیر یا secret ناقص
- `InvariantViolation`: bug یا state غیرمجاز

فقط orchestrator policy حق retry دارد. adapter داخل خودش retry پنهان انجام نمی‌دهد، مگر retry سطح HTTP کوتاه و مستند.

هیچ `except Exception: pass` مجاز نیست. خطای غیرمنتظره با correlation context ثبت و به boundary مناسب propagate می‌شود.

## 6. Logging

- log ساختاریافته؛ استفاده از print ممنوع به‌جز scriptهای توسعه.
- token، cookie، authorization header و محتوای credential هرگز log نشود.
- پیام log انگلیسی و پایدار؛ متن UI می‌تواند فارسی باشد.
- هر job context شامل `project_id`, `building_id`, `stage`, `attempt_id` است.
- تصویر یا HTML کامل صفحه فقط در debug artifact محافظت‌شده ذخیره شود.

## 7. Database

- migration برای هر تغییر schema اجباری است.
- transaction boundary در application service تعیین می‌شود.
- SQLite foreign keys فعال و WAL mode استفاده شود.
- queryهای تکراری repository دارند.
- soft delete برای entityهای user-visible.
- migration destructive بدون backup و مسیر rollback پذیرفته نیست.

## 8. Browser Adapter

- selectorها مرکزی، نام‌دار و versioned باشند.
- از waitهای condition-based استفاده شود؛ sleep ثابت ممنوع مگر با توجیه.
- timeout هر عملیات مشخص باشد.
- download با event مرورگر و validation فایل انجام شود.
- adapter contract باید بدون سایت واقعی با fixture HTML قابل‌آزمایش باشد.
- تغییر UI provider فقط package همان provider را تغییر دهد.

## 9. Files and Artifacts

- write به‌صورت temp → flush → hash → validate → atomic rename.
- فایل ورودی کاربر overwrite نمی‌شود.
- هر artifact دارای manifest و lineage است.
- hash با SHA-256.
- image metadata حساس قبل از export نهایی بررسی شود.

## 10. API

- routeها thin و use caseها testable باشند.
- breaking change نیازمند `/v2` یا migration contract است.
- idempotency برای commandهای طولانی اجباری است.
- error response مطابق envelope مشترک.
- enumهای wire format lowercase و پایدار.

## 11. Git و Review

- commit کوچک و موضوع‌محور با conventional prefix: `feat`, `fix`, `test`, `docs`, `refactor`, `chore`.
- PR باید test plan و risk/rollback note داشته باشد.
- کد provider automation بدون screenshot/fixture تست و failure diagnostics merge نشود.
- تغییر state machine نیازمند به‌روزرسانی PRD/Data Flow و migration test است.

## 12. Definition of Done

- acceptance criteria پیاده شده است.
- unit/integration tests مرتبط وجود دارد.
- log و error message قابل‌فهم است.
- retry/restart سناریو بررسی شده است.
- secret leakage test پاس می‌شود.
- docs/API/migration در صورت نیاز به‌روز شده‌اند.

