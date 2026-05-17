# 🐾 HayvonMarket — O'zbekiston Hayvonlar Savdosi Platformasi

## 🚀 Ishga tushirish (Local)

```bash
# 1. Kutubxonalarni o'rnating
pip install flask

# 2. .env fayl yarating
cp .env.example .env
# .env faylini oching va ANTHROPIC_API_KEY kiriting

# 3. Ishga tushiring
python app.py
# http://127.0.0.1:5000 da oching
```

## 🔑 AI Chat uchun API kalit

AI Chat ishlashi uchun Anthropic API kaliti kerak:

1. https://console.anthropic.com ga kiring
2. "API Keys" bo'limidan yangi kalit oling
3. `.env` fayliga qo'shing:
   ```
   ANTHROPIC_API_KEY=sk-ant-api03-SIZNING_KALITINGIZ
   ```

## 🌐 Railway.app da Deploy

1. Railway.app ga kiring → New Project → GitHub repo tanlang
2. **Variables** bo'limiga qo'shing:
   - `ANTHROPIC_API_KEY` = `sk-ant-api03-...`
   - `SECRET_KEY` = (ixtiyoriy, o'zingiz o'ylang)
3. Deploy tugmachasini bosing ✅

## 👤 Demo Foydalanuvchilar

| Login | Parol | Rol |
|-------|-------|-----|
| admin | admin123 | Admin |
| sardor | demo123 | Sotuvchi |

## 🛠 Texnologiyalar

- **Backend**: Flask (Python)
- **Database**: SQLite
- **AI**: Anthropic Claude Sonnet
- **Frontend**: Vanilla HTML/CSS/JS
