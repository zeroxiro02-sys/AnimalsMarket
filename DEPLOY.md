# 🚀 Railway Deployment Guide — HayvonMarket

## 1. Сайтни Railway'ga deploy qilish

### Tayyorgarlik
1. [railway.app](https://railway.app) ga kiring (GitHub bilan)
2. **New Project** → **Deploy from GitHub repo** bosing
3. Repo'ingizni tanlang yoki zip'ni yuklang

### Agar GitHub repo yo'q bo'lsa:
1. [github.com](https://github.com) da yangi repo yarating
2. Papkani GitHub'ga push qiling:
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/SIZNING_USERNAME/hayvonmarket.git
git push -u origin main
```
3. Railway'da GitHub repo'ni tanlang

---

## 2. Environment Variables (Muhim!)

Railway dashboard'da **Variables** bo'limiga kiring va quyidagilarni qo'shing:

```
GOOGLE_CLIENT_ID=879793779405-l4n2jacp3dtb5h5rcm9or5i4deosr8bk.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-...yangi_secret...
SECRET_KEY=hayvon-market-super-random-secret-key-2024
DATABASE_PATH=/app/instance/db.sqlite3
```

⚠️ SECRET_KEY ni o'zgartiring — tasodifiy uzun string bo'lishi kerak!

---

## 3. Google OAuth'ni yangilash (MUHIM!)

Deploy bo'lgandan so'ng Railway sizga URL beradi, masalan:
`https://hayvonmarket-production.up.railway.app`

Bu URL'ni Google Cloud Console'da qo'shing:

1. [console.cloud.google.com](https://console.cloud.google.com) → Google Auth Platform → Clients → AnimalsMarket
2. **Authorized redirect URIs** ga qo'shing:
   ```
   https://hayvonmarket-production.up.railway.app/auth/google/callback
   ```
3. **Save** bosing

---

## 4. OAuth Consent Screen — Publish

Google'da login barcha foydalanuvchilarga ochiq bo'lishi uchun:

1. Google Auth Platform → **Audience**
2. **Publishing status** → **Publish App** bosing
3. Confirm qiling

---

## 5. Persistent Storage (Database)

Railway'da SQLite fayli har deploy'da o'chib ketishi mumkin.
Uzoq muddatli ishlatish uchun **Railway Volume** qo'shing:

1. Railway project → **+ Add** → **Volume**
2. Mount path: `/app/instance`
3. Bu database'ni saqlaydi

---

## ✅ Tekshirish

Deploy bo'lgandan so'ng:
- `https://your-url.up.railway.app` — asosiy sahifa
- `https://your-url.up.railway.app/login` — Google login

Muammo bo'lsa Railway'da **Logs** bo'limini tekshiring.
