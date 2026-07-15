# Near Project Environment — Documentation

این پوشه مرجع محصول و معماری MVP سامانه تولید خودکار مدل سه‌بعدی ساختمان‌های اطراف پروژه است.

## اسناد

1. [Vision](./01-vision.md)
2. [PRD](./02-prd.md)
3. [Technical Architecture](./03-technical-architecture.md)
4. [Tech Stack](./04-tech-stack.md)
5. [Data Flow](./05-data-flow.md)
6. [API Design](./06-api-design.md)
7. [Folder Structure](./07-folder-structure.md)
8. [Coding Standards](./08-coding-standards.md)
9. [Testing Strategy](./09-testing-strategy.md)
10. [Risk Analysis](./10-risk-analysis.md)

## تصمیم‌های کلیدی MVP

- اجرا روی یک کامپیوتر اختصاصی Windows
- معماری Modular Monolith و Local-first
- رابط دسکتاپ برای سه مرحله تأیید انسانی
- استفاده از مرورگر با پروفایل اختصاصی و نشست‌های ازپیش‌فعال
- کنترل وب ChatGPT و Hunyuan از طریق آداپترهای مجزا
- SQLite به‌عنوان منبع حقیقت وضعیت پروژه و پردازش
- ذخیره فایل‌ها روی دیسک محلی با ساختار قابل‌ردیابی
- دو تلاش خودکار و سپس انتقال به `NeedsReview`
- Telegram فقط برای اعلان؛ تأیید داخل برنامه انجام می‌شود
- مدل‌های FBX مستقل، با واحد متر و ارتفاع تنظیم‌شده

## ترتیب پیشنهادی مطالعه

برای تصمیم‌گیری محصول: Vision → PRD → Risk Analysis  
برای پیاده‌سازی: Technical Architecture → Data Flow → API Design → Tech Stack → Folder Structure → Coding Standards → Testing Strategy

