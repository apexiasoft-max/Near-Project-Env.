# Folder Structure

## 1. ساختار repository

```text
near-project-environment/
├── pyproject.toml
├── uv.lock
├── README.md
├── docs/
├── migrations/
├── scripts/
├── src/
│   └── npe/
│       ├── main.py
│       ├── bootstrap.py
│       ├── domain/
│       │   ├── projects/
│       │   ├── buildings/
│       │   ├── workflows/
│       │   ├── approvals/
│       │   └── artifacts/
│       ├── application/
│       │   ├── commands/
│       │   ├── queries/
│       │   ├── services/
│       │   └── ports/
│       ├── infrastructure/
│       │   ├── database/
│       │   ├── filesystem/
│       │   ├── browser/
│       │   │   ├── google/
│       │   │   ├── neshan/
│       │   │   ├── chatgpt/
│       │   │   └── hunyuan/
│       │   ├── vision/
│       │   ├── geo/
│       │   ├── blender/
│       │   └── telegram/
│       ├── api/
│       │   ├── routes/
│       │   ├── schemas/
│       │   └── dependencies.py
│       ├── desktop/
│       │   ├── views/
│       │   ├── viewmodels/
│       │   ├── widgets/
│       │   └── resources/
│       ├── worker/
│       │   ├── orchestrator.py
│       │   ├── runner.py
│       │   └── recovery.py
│       └── shared/
│           ├── config.py
│           ├── errors.py
│           ├── logging.py
│           └── types.py
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   ├── e2e/
│   ├── fixtures/
│   └── golden/
└── packaging/
    ├── installer/
    └── playwright/
```

## 2. ساختار داده برنامه

```text
%PROGRAMDATA%/NearProjectEnvironment/
├── app.db
├── backups/
├── logs/
├── browser-profile/
├── browser-traces/
├── models/
└── runtime/
```

secretها در این مسیر به‌صورت plaintext قرار نمی‌گیرند و از Windows Credential Manager استفاده می‌شود.

## 3. ساختار هر پروژه

```text
Project_Name__<short-id>/
├── project.json
├── overview/
│   ├── aerial_original.<ext>
│   ├── aerial_coded.png
│   └── buildings.csv
├── reference_pool/
│   ├── inbox/
│   ├── indexed/
│   └── index.json
├── buildings/
│   ├── B001/
│   │   ├── metadata.json
│   │   ├── references/
│   │   │   ├── raw/
│   │   │   ├── selected/
│   │   │   └── manifest.json
│   │   ├── generated/
│   │   │   ├── attempts/
│   │   │   │   └── 001/
│   │   │   │       ├── sheet_original.png
│   │   │   │       ├── front.png
│   │   │   │       ├── back.png
│   │   │   │       ├── left.png
│   │   │   │       ├── right.png
│   │   │   │       └── top.png
│   │   │   └── approved/
│   │   ├── model/
│   │   │   ├── raw/
│   │   │   ├── final/B001.fbx
│   │   │   └── validation.json
│   │   └── debug/
│   └── B002/
├── reports/
│   ├── process_report.html
│   └── audit.jsonl
└── temp/
```

## 4. قواعد نام‌گذاری فایل

- شناسه ساختمان ثابت و zero-padded: `B001`.
- نام artifact تولیدی شامل نقش است، نه متن آزاد.
- attemptها افزایشی و immutable هستند.
- فایل نهایی فقط پس از validation به `final` منتقل می‌شود.
- pathهای ثبت‌شده در DB نسبت به root پروژه هستند.
- نام پروژه sanitize می‌شود؛ شناسه کوتاه از collision جلوگیری می‌کند.
- فایل موقت پسوند `.partial` دارد.

## 5. فایل `project.json`

این فایل برای portability و خوانایی انسانی است، اما database منبع حقیقت runtime باقی می‌ماند. شامل schema version، مختصات، شعاع، زمان ایجاد و شناسه پروژه است و secret یا cookie ندارد.

## 6. Reference Pool دستی

تیم تصاویر را در `reference_pool/inbox` قرار می‌دهد. عملیات Import فایل‌ها را hash، deduplicate و تحلیل می‌کند و نسخه indexشده را در `indexed` قرار می‌دهد. سیستم هیچ تصویر محله‌ای را برای تکمیل این پوشه خودکار جمع‌آوری نمی‌کند.

