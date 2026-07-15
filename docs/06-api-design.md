# API Design

## 1. هدف

API محلی مرز بین Desktop UI، orchestrator و worker است. این API عمومی یا شبکه‌ای نیست و فقط روی `127.0.0.1` ارائه می‌شود. قراردادها versioned و OpenAPI-generated هستند.

Base path: `/api/v1`

## 2. قواعد عمومی

- JSON با UTF-8؛ زمان‌ها ISO 8601 UTC.
- شناسه‌ها UUIDv7؛ کد ساختمان user-facing مانند `B001` جداست.
- عملیات طولانی `202 Accepted` و `operation_id` برمی‌گردانند.
- mutationها `Idempotency-Key` می‌پذیرند.
- optimistic concurrency با فیلد `version` انجام می‌شود.
- path فایل مطلق از API خارج نمی‌شود؛ artifact با ID ارائه می‌شود.
- local session token در header داخلی ارسال می‌شود.

## 3. Error Envelope

```json
{
  "error": {
    "code": "REFERENCE_NOT_FOUND",
    "message": "No suitable reference was found for building B004.",
    "retryable": false,
    "details": {"building_id": "..."},
    "correlation_id": "..."
  }
}
```

## 4. Project Endpoints

### `POST /projects`

```json
{
  "name": "Jordan-01",
  "latitude": 35.7751,
  "longitude": 51.4142,
  "radius_m": 200,
  "output_root": "D:/NPE-Projects"
}
```

### `GET /projects`

فهرست پروژه‌ها با progress summary.

### `GET /projects/{project_id}`

جزئیات، health، counts و stage پروژه.

### `POST /projects/{project_id}/start`

اجرای preflight و آغاز pipeline.

### `POST /projects/{project_id}/pause`

توقف پس از safe checkpoint.

### `POST /projects/{project_id}/resume`

ادامه jobهای واجد شرایط.

### `POST /projects/{project_id}/cancel`

لغو jobهای آینده؛ artifactهای موجود حفظ می‌شوند.

### `GET /projects/{project_id}/report`

گزارش ساختاریافته؛ export HTML endpoint جدا دارد.

## 5. Building Endpoints

### `GET /projects/{project_id}/buildings`

filterهای `status`, `needs_review`, `code` را می‌پذیرد.

### `POST /projects/{project_id}/buildings`

افزودن دستی footprint و metadata اولیه.

### `GET /buildings/{building_id}`

جزئیات کامل و timeline.

### `PATCH /buildings/{building_id}`

```json
{
  "version": 4,
  "footprint_geojson": {"type": "Polygon", "coordinates": []},
  "approved_height_m": 24.0,
  "approved_floor_count": 8,
  "front_bearing_deg": 135.0
}
```

### `DELETE /buildings/{building_id}`

Soft delete؛ کد ساختمان reuse نمی‌شود.

## 6. Approval Endpoints

### `POST /projects/{project_id}/approvals/map`

تأیید batch با snapshot version ساختمان‌ها.

### `POST /buildings/{building_id}/approvals/reference`

```json
{
  "reference_artifact_ids": ["..."],
  "front_bearing_deg": 135,
  "comment": "Use the second image as facade reference."
}
```

### `POST /buildings/{building_id}/approvals/views`

شناسه پنج view و comment را ثبت می‌کند.

### `POST /projects/{project_id}/approvals/references:batch`

تأیید گروهی موارد انتخاب‌شده با نتیجه مستقل برای هر ساختمان.

### `POST /projects/{project_id}/approvals/views:batch`

تأیید گروهی view setها.

## 7. Reference Pool

### `POST /projects/{project_id}/reference-pool/import`

فایل‌های قرارگرفته در پوشه دستی را scan و index می‌کند؛ سیستم تصویری از محله جمع‌آوری نمی‌کند.

### `GET /projects/{project_id}/reference-pool`

فهرست و وضعیت تحلیل تصاویر دستی.

### `POST /buildings/{building_id}/references/collect`

جمع‌آوری reference واقعی ساختمان از providerها را اجرا می‌کند.

### `POST /buildings/{building_id}/references/{artifact_id}/select`

انتخاب candidate برای تأیید.

## 8. Stage Control

### `POST /buildings/{building_id}/stages/{stage}/run`

اجرای stage در صورت برقراری prerequisite.

### `POST /buildings/{building_id}/stages/{stage}/retry`

شروع attempt دستی جدید و reset محدودیت retry همان stage.

### `POST /buildings/{building_id}/stages/{stage}/skip`

فقط برای stageهای explicitly skippable و با ثبت دلیل.

### `GET /operations/{operation_id}`

```json
{
  "id": "...",
  "status": "running",
  "progress": 0.55,
  "stage": "GeneratingViews",
  "building_code": "B006"
}
```

## 9. Artifact Endpoints

### `GET /artifacts/{artifact_id}/content`

stream محلی فایل برای نمایش UI.

### `GET /artifacts/{artifact_id}/metadata`

hash، lineage، size، dimensions و producer.

### `POST /buildings/{building_id}/artifacts/upload`

آپلود دستی reference یا جایگزینی artifact با type محدود.

## 10. Settings and Health

### `GET /health`

وضعیت database، disk، browser، Blender و worker.

### `POST /preflight`

health check کامل providerها و Telegram.

### `GET /settings`

تنظیمات غیرحساس.

### `PATCH /settings`

مسیرها، timeoutها، chat ID و policyها. token از endpoint جدا و secret-aware ذخیره می‌شود.

### `PUT /settings/secrets/telegram-token`

token را در Windows Credential Manager ذخیره می‌کند و هرگز آن را برنمی‌گرداند.

### `POST /notifications/telegram/test`

ارسال پیام آزمایشی.

## 11. Event Stream

UI برای progress زنده از `GET /events` با Server-Sent Events استفاده می‌کند. eventها شامل `project.updated`, `building.stage_changed`, `operation.progress`, `approval.required`, `notification.failed` هستند.

SSE برای MVP از WebSocket ساده‌تر است و ارتباط یک‌طرفه موردنیاز را پوشش می‌دهد.

