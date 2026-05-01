# 🐄 AnimalsMarket — Hayvonlar savdosi platformasi

O'zbekistondagi hayvonlar savdosi uchun zamonaviy onlayn platforma.

---

## 🚀 Railway orqali deploy qilish

### 1-qadam: GitHub ga yuklash

```bash
git init
git add .
git commit -m "Initial commit: AnimalsMarket"
git branch -M main
git remote add origin https://github.com/USERNAME/hayvonmarket.git
git push -u origin main
```

### 2-qadam: Railway da project ochish

1. [railway.app](https://railway.app) ga kiring
2. **"New Project" → "Deploy from GitHub repo"** ni tanlang
3. Repositoriyangizni tanlang — deploy avtomatik boshlanadi

### 3-qadam: Muhit o'zgaruvchilari

Railway dashboardida **Variables** bo'limiga qo'shing:

| O'zgaruvchi    | Qiymat                            |
|----------------|-----------------------------------|
| `SECRET_KEY`   | `uzingiz-tasodifiy-kalit-2026`    |
| `FLASK_ENV`    | `production`                      |
| `DATABASE_PATH`| `/tmp/hayvonmarket.db`            |

> ⚠️ SECRET_KEY ni albatta o'zgartiring!

### 4-qadam: Tayyor!

Railway HTTPS URL beradi. Admin: `/admin/` — login: `admin` / `admin123`

---

## 💻 Lokal ishga tushirish

```bash
pip install -r requirements.txt
python app.py
# http://127.0.0.1:5000
```

---

## 📱 Yangiliklar

- ✅ **Mobil pastki navigatsiya** — telefon uchun qulay bottom nav bar
- ✅ **12 viloyat** (Sirdaryo va Jizzax olib tashlandi)
- ✅ **Railway ready** — Procfile, nixpacks.toml, railway.json
- ✅ **Responsive dizayn** yaxshilandi

## 🗺️ 12 Viloyat

Toshkent sh., Toshkent vil., Samarqand, Buxoro, Andijon, Farg'ona,
Namangan, Qashqadaryo, Surxondaryo, Xorazm, Navoiy, Qoraqalpog'iston
