# Live one-building release smoke

این Smoke فقط برای Release Candidate و روی کامپیوتر اختصاصی اجرا می‌شود. Secret، Cookie، Browser Profile، تصویر دارای اطلاعات شخصی و فایل خام Provider نباید Commit شوند.

## پیش‌نیاز

- برنامه و worker از همان Commit کاندید اجرا شوند.
- Chrome profile اختصاصی باز و ChatGPT و Hunyuan Login باشند.
- یک ساختمان تهران با aerial، footprint، ارتفاع هدف و حداقل یک reference تأییدشده انتخاب شود.

## اجرا

1. Project و ساختمان B001 را بسازید و Map approval را ثبت کنید.
2. reference منتخب را تأیید و پنج نما را تولید کنید.
3. Front/Back/Left/Right/Top را بازبینی و approval کنید.
4. پنج فایل را در فیلدهای متناظر Hunyuan بارگذاری و Job را آغاز کنید.
5. دانلود FBX را دستی انجام دهید و فایل را در برنامه Register کنید.
6. Normalize/scale را اجرا و FBX نهایی را دوباره Import کنید.
7. Delivery package را بسازید و `package_manifest.json`، `overview/buildings.csv` و گزارش HTML را بازبینی کنید.

## معیار عبور

- B001 در گزارش `Completed` است.
- پنج view مستقل و reference منتخب قابل بازشدن‌اند.
- raw model و final FBX موجود و checksum آنها صحیح است.
- ارتفاع FBX نهایی با هدف، در تلورانس pipeline است.
- هیچ Secret یا مسیر خارج از Project root در manifest وجود ندارد.
- زمان فعال انسان، runtime، خطاها و نتیجه Pass/Fail در گزارش Release ثبت شده‌اند.

Logout، CAPTCHA، خطای آپلود یا دانلود نتیجه را Fail/NeedsReview می‌کند؛ خطا نباید با تکرار دستی پنهان شود.
