# Tech Stack

## انتخاب پیشنهادی

| بخش | فناوری | دلیل |
|---|---|---|
| زبان اصلی | Python 3.12 | اکوسیستم قوی vision، geo، automation و Blender |
| Desktop UI | PySide6 + Qt | رابط بومی ویندوز، مناسب dashboard و ویرایش تصویر |
| Local API | FastAPI + Pydantic v2 | قرارداد typed، مستندسازی OpenAPI و جداسازی UI/worker |
| ORM/Migration | SQLAlchemy 2 + Alembic | transaction و migration پایدار |
| Database | SQLite با WAL | local-first، بدون سرویس جدا، backup ساده |
| Job Queue | صف پایدار مبتنی بر SQLite | مناسب یک ماشین؛ بدون Redis و پیچیدگی اضافه |
| Browser | Playwright Python | persistent context، upload/download و trace مناسب |
| HTTP | httpx | async client برای Telegram و سرویس‌های مجاز |
| Image | Pillow + OpenCV | crop، annotation، quality checks و geometry |
| Geo | Shapely + pyproj + GeoPandas | footprint، radius، projection و اندازه‌گیری متریک |
| Detection | ONNX Runtime | اجرای local مدل segmentation بدون وابستگی cloud |
| 3D | Blender LTS headless | import/export FBX، اندازه‌گیری، scale و validation |
| Mesh inspection | trimesh | checks سبک پیش از/پس از Blender، در حد پشتیبانی فرمت |
| Telegram | Telegram Bot HTTP API | اعلان ساده بدون framework سنگین |
| Logging | structlog | log ساختاریافته و context binding |
| Packaging | PyInstaller | تولید executable؛ installer با Inno Setup یا WiX |
| Tests | pytest + pytest-qt + Playwright | unit، UI و adapter contract |
| Quality | Ruff + Black + mypy | lint، format و type checking |

## نکات انتخاب

### چرا Modular Monolith و SQLite؟

محصول روی یک کامپیوتر و برای یک تیم اجرا می‌شود. PostgreSQL، Redis و microservice در MVP هزینه عملیاتی بی‌دلیل ایجاد می‌کنند. abstraction صف و repository باید طوری باشد که ارتقای آینده ممکن بماند.

### چرا Blender برای FBX؟

FBX فرمت proprietary و پشتیبانی کتابخانه‌های pure Python از آن محدود است. Blender مسیر عملی و قابل‌آزمایش برای import، بررسی ابعاد، scale و export مجدد فراهم می‌کند.

### چرا Playwright؟

نیاز به session پایدار، مشاهده DOM، upload فایل، انتظار رویداد download، screenshot و trace داریم. provider adapterها باید Playwright را پشت interface پنهان کنند.

## مدیریت نسخه‌ها

- Python و dependencyها با lockfile دقیق pin شوند.
- Playwright browser version همراه release pin شود.
- Blender فقط روی یک نسخه LTS تأییدشده پشتیبانی شود.
- selector schema هر provider version داشته باشد.
- مدل ONNX همراه checksum و model card داخلی نگهداری شود.

## وابستگی‌های اختیاری/مرحله‌ای

- OCR برای برچسب‌ها فقط اگر crop template کافی نباشد.
- مدل segmentation ساختمان پس از spike و benchmark انتخاب می‌شود.
- اگر footprint قابل‌اعتماد از منبع مجاز در دسترس باشد، provider آن می‌تواند قبل از vision قرار گیرد.

## مواردی که فعلاً انتخاب نمی‌شوند

- Electron/.NET برای UI: یکپارچگی با pipeline پایتون را پیچیده می‌کند.
- Celery/Redis: برای یک ماشین بیش‌ازحد سنگین است.
- Kubernetes/Cloud deployment: خلاف مدل local-first MVP است.
- Telegram bot framework: برای اعلان یک‌طرفه لازم نیست.

