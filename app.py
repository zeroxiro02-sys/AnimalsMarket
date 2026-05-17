"""
HayvonMarket — Hayvonlar savdosi platformasi
Flask web application (Django-style: MVC, ORM, Admin, Auth)
Run: python app.py
Open: http://127.0.0.1:5000
Admin: admin / admin123
Demo:  sardor / demo123
"""
import os, sqlite3, hashlib, secrets, json, re
from functools import wraps
from datetime import datetime

# Load .env file if present (for local development)
try:
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(_env_path):
        with open(_env_path) as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith('#') and '=' in _line:
                    _k, _v = _line.split('=', 1)
                    os.environ.setdefault(_k.strip(), _v.strip())
except Exception:
    pass

from flask import (Flask, render_template, request, redirect,
                   url_for, session, flash, g, jsonify, abort)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def _read_api_key():
    """Read ANTHROPIC_API_KEY from .api_key file if env var not set."""
    try:
        kf = os.path.join(BASE_DIR, '.api_key')
        if os.path.exists(kf):
            return open(kf).read().strip()
    except Exception:
        pass
    return ''
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'hayvon-market-ultra-secret-key-2024')
_default_db = os.path.join(BASE_DIR, 'instance', 'db.sqlite3')
# Railway: use /tmp for writable SQLite storage
if os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('RAILWAY_PROJECT_ID'):
    _default_db = '/tmp/hayvonmarket.sqlite3'
DATABASE = os.environ.get('DATABASE_PATH', _default_db)

ANIMAL_TYPES = [
    ('sigir',    '🐄', "Sigir"),
    ('qoy',      '🐑', "Qo'y"),
    ('echki',    '🐐', "Echki"),
    ('ot',       '🐴', "Ot"),
    ('tovuq',    '🐓', "Tovuq"),
    ('o_rdak',   '🦆', "O'rdak"),
    ('g_oz',     '🪿', "G'oz"),
    ('quyon',    '🐇', "Quyon"),
    ('qoramol',  '🐂', "Qoramol/Buqa"),
    ('tuyoqli',  '🐪', "Tuya"),
    ('boshqa',   '🐾', "Boshqa"),
]
REGIONS = ['Toshkent sh.','Toshkent vil.','Samarqand','Buxoro',
           "Andijon","Farg'ona","Namangan","Qashqadaryo",
           "Surxondaryo","Xorazm","Navoiy",
           "Qoraqalpog'iston"]

DELIVERY_PERSONS = [
    {'id':'d1','avatar':'J','name':'Jasur Toshmatov','region':'Toshkent sh.','deliveries':142,'rating':4.9,'reviews':38,'price':'30,000 so\'m'},
    {'id':'d2','avatar':'S','name':'Sardor Raximov','region':'Samarqand','deliveries':87,'rating':4.8,'reviews':24,'price':'25,000 so\'m'},
    {'id':'d3','avatar':'B','name':'Bobur Nazarov','region':"Farg'ona",'deliveries':63,'rating':4.7,'reviews':17,'price':'28,000 so\'m'},
    {'id':'d4','avatar':'O','name':'Otabek Mirzayev','region':'Buxoro','deliveries':55,'rating':4.6,'reviews':12,'price':'22,000 so\'m'},
]

VETS = [
    {'id':'v1','avatar':'K','name':'Dr. Kamoliddin Nazarov','region':'Toshkent','exp':15,'spec':'Yirik hayvonlar','rating':4.9,'reviews':34,'last_review':'Juda malakali shifokor, tavsiya qilaman!'},
    {'id':'v2','avatar':'N','name':'Dr. Nilufar Rahimova','region':'Samarqand','exp':10,'spec':'Chorva mollar','rating':4.8,'reviews':28,'last_review':'Tez va sifatli xizmat ko\'rsatdi.'},
    {'id':'v3','avatar':'J','name':'Dr. Jasur Yusupov','region':"Farg'ona",'exp':8,'spec':'Ot, sigir','rating':4.7,'reviews':19,'last_review':None},
    {'id':'v4','avatar':'S','name':'Dr. Shahnoza Mirzayeva','region':'Buxoro','exp':12,'spec':'Parrandalar','rating':4.6,'reviews':22,'last_review':'Parrandalar bo\'yicha eng yaxshi mutaxassis!'},
]

# ─── DB helpers ────────────────────────────────────────────────
def get_db():
    if 'db' not in g:
        os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db: db.close()

def init_db():
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        username   TEXT UNIQUE NOT NULL,
        password   TEXT NOT NULL,
        role       TEXT DEFAULT 'buyer',
        full_name  TEXT DEFAULT '',
        phone      TEXT DEFAULT '',
        region     TEXT DEFAULT '',
        email      TEXT DEFAULT '',
        bio        TEXT DEFAULT '',
        avatar_letter TEXT DEFAULT '',
        rating     REAL DEFAULT 5.0,
        total_sales INTEGER DEFAULT 0,
        is_verified INTEGER DEFAULT 0,
        is_admin   INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS listings (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id      INTEGER NOT NULL,
        title        TEXT NOT NULL,
        animal_slug  TEXT NOT NULL,
        animal_emoji TEXT DEFAULT '🐾',
        animal_name  TEXT DEFAULT '',
        price        INTEGER NOT NULL,
        region       TEXT NOT NULL,
        district     TEXT DEFAULT '',
        age          TEXT DEFAULT '',
        gender       TEXT DEFAULT '',
        breed        TEXT DEFAULT '',
        count        INTEGER DEFAULT 1,
        weight       TEXT DEFAULT '',
        description  TEXT DEFAULT '',
        photos       TEXT DEFAULT '',
        is_active    INTEGER DEFAULT 1,
        is_premium   INTEGER DEFAULT 0,
        is_sold      INTEGER DEFAULT 0,
        is_reserved  INTEGER DEFAULT 0,
        reserved_by  INTEGER DEFAULT NULL,
        reserved_at  TEXT DEFAULT NULL,
        views        INTEGER DEFAULT 0,
        latitude     REAL DEFAULT NULL,
        longitude    REAL DEFAULT NULL,
        created_at   TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS messages (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        from_id      INTEGER NOT NULL,
        to_id        INTEGER NOT NULL,
        listing_id   INTEGER,
        body         TEXT NOT NULL,
        is_read      INTEGER DEFAULT 0,
        created_at   TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(from_id) REFERENCES users(id),
        FOREIGN KEY(to_id)   REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS favorites (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL,
        listing_id INTEGER NOT NULL,
        UNIQUE(user_id, listing_id)
    );
    CREATE TABLE IF NOT EXISTS reviews (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        from_id INTEGER NOT NULL,
        to_id   INTEGER NOT NULL,
        rating  INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
        body    TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now'))
    );
    """)
    # Migrate: add missing columns if they don't exist
    cols = [r[1] for r in db.execute("PRAGMA table_info(listings)").fetchall()]
    if 'latitude' not in cols:
        db.execute("ALTER TABLE listings ADD COLUMN latitude REAL DEFAULT NULL")
    if 'longitude' not in cols:
        db.execute("ALTER TABLE listings ADD COLUMN longitude REAL DEFAULT NULL")
    if 'is_reserved' not in cols:
        db.execute("ALTER TABLE listings ADD COLUMN is_reserved INTEGER DEFAULT 0")
    if 'reserved_by' not in cols:
        db.execute("ALTER TABLE listings ADD COLUMN reserved_by INTEGER DEFAULT NULL")
    if 'reserved_at' not in cols:
        db.execute("ALTER TABLE listings ADD COLUMN reserved_at TEXT DEFAULT NULL")
    if 'photos' not in cols:
        db.execute("ALTER TABLE listings ADD COLUMN photos TEXT DEFAULT ''")

    if db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        _seed(db)
    db.commit()
    db.close()

def _seed(db):
    def hp(p): return hashlib.sha256(p.encode()).hexdigest()
    db.execute("""INSERT INTO users (username,password,full_name,phone,region,bio,rating,total_sales,is_verified,is_admin,avatar_letter)
                  VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
               ('admin',hp('admin123'),'Administrator','','','',5.0,0,1,1,'A'))
    sellers = [
        ('sardor',  hp('demo123'),'Sardor Abdullayev','+998901234567','Samarqand',
         "10 yildan beri chorvachilik bilan shug'ullanaman.",4.9,23,1,'S'),
        ('aziz',    hp('demo123'),'Aziz Karimov','+998912345678',"Toshkent vil.",
         "Qo'y va echki fermasi. Barcha hayvonlar emlangan.",4.7,15,1,'A'),
        ('malika',  hp('demo123'),'Malika Yusupova','+998933456789','Buxoro',
         "Oilaviy ferma. 20 yillik tajriba.",4.8,31,1,'M'),
        ('bobur',   hp('demo123'),'Bobur Toshmatov','+998944567890',"Farg'ona",
         "Otchilik mutaxassisi. Zotli otlar.",4.6,8,0,'B'),
    ]
    for row in sellers:
        db.execute("""INSERT INTO users (username,password,full_name,phone,region,bio,rating,total_sales,is_verified,avatar_letter)
                      VALUES (?,?,?,?,?,?,?,?,?,?)""", row)
    uids = {r['username']:r['id'] for r in db.execute("SELECT id,username FROM users").fetchall()}
    listings = [
        (uids['sardor'],'Sut sigiri — Holstein zoti','sigir','🐄',"Sigir",12000000,
         'Samarqand','Urgut','4 yosh',"Urg'ochi",'Holstein',1,'350 kg',
         "Kuniga 25 litr sut beradi. Sog'lom, emlangan. Barcha hujjatlari bor.",1,1),
        (uids['aziz'],"Qo'y (3 bosh)",'qoy','🐑',"Qo'y",4500000,
         "Toshkent vil.",'Zangiota','2-3 yosh','Aralash',"O'zbek zoti",3,'65 kg',
         "Uchta qo'y. Sog'lom, semiz, emlangan.",1,0),
        (uids['bobur'],'Zotli Arab oti','ot','🐴',"Ot",25000000,
         "Farg'ona",'Marg\'ilon','5 yosh','Erkak','Arab zoti',1,'480 kg',
         "Toza zotli, mashg'ullanilgan, hujjatli. Poyga uchun.",1,1),
        (uids['aziz'],'Echki (2 bosh) — sut zoti','echki','🐐',"Echki",2800000,
         "Toshkent vil.",'Kibray','1-2 yosh',"Urg'ochi",'Zanen',2,'42 kg',
         "Sut echkilari. Har biri kuniga 3 litr sut.",1,0),
        (uids['malika'],'Broiler tovuq (20 bosh)','tovuq','🐓',"Tovuq",1200000,
         'Buxoro','Buxoro sh.','45 kunlik','Aralash','Broiler',20,'2.5 kg',
         "Tayyor savdo uchun. Vazni 2.5-3 kg.",1,0),
        (uids['sardor'],"Qoramol — go'sht uchun",'qoramol','🐂',"Qoramol",8500000,
         'Samarqand','Samarqand sh.','3 yosh','Erkak','Aralash',1,'380 kg',
         "380 kg. Go'sht uchun semirtirilgan.",1,0),
        (uids['malika'],"Qo'y (5 bosh) — Gissar",'qoy','🐑',"Qo'y",9000000,
         'Buxoro','Kogon','2-4 yosh','Erkak','Gissar',5,'80 kg',
         "Gissar zoti. Semiz, sog'lom.",1,1),
        (uids['bobur'],'Sut sigiri — Simmental','sigir','🐄',"Sigir",15000000,
         "Farg'ona","Farg'ona sh.",'5 yosh',"Urg'ochi",'Simmental',1,'420 kg',
         "Oyiga 700 litr sut. Hujjatlar mavjud.",1,0),
        (uids['aziz'],"O'rdak (10 bosh)",'o_rdak','🦆',"O'rdak",800000,
         "Toshkent vil.",'Chinoz','3 oylik','Aralash','Pekin zoti',10,'1.8 kg',
         "Pekin zoti. Ozuqa bilan birga.",1,0),
        (uids['malika'],"G'oz (6 bosh)",'g_oz','🪿',"G'oz",1500000,
         'Buxoro','Shofirkon','4 oylik','Aralash','Oddiy',6,'3 kg',
         "Katta g'ozlar.",1,0),
    ]
    for i,l in enumerate(listings):
        db.execute("""INSERT INTO listings
            (user_id,title,animal_slug,animal_emoji,animal_name,price,region,district,
             age,gender,breed,count,weight,description,is_active,is_premium,views)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            l[:16] + (secrets.randbelow(300)+20,))
    # Demo reviews
    db.execute("INSERT INTO reviews (from_id,to_id,rating,body) VALUES (?,?,?,?)",
               (uids['aziz'],uids['sardor'],5,"Juda ishonchli sotuvchi! Hayvon tasvirda ko'ringanidek."))
    db.execute("INSERT INTO reviews (from_id,to_id,rating,body) VALUES (?,?,?,?)",
               (uids['malika'],uids['sardor'],5,"Tez javob berdi. Hammasi yaxshi bo'ldi."))
    db.execute("INSERT INTO reviews (from_id,to_id,rating,body) VALUES (?,?,?,?)",
               (uids['sardor'],uids['aziz'],4,"Yaxshi sotuvchi, hayvon sog'lom edi."))

# ─── Auth helpers ──────────────────────────────────────────────
def hp(p): return hashlib.sha256(p.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def deco(*a,**kw):
        if 'uid' not in session:
            flash("Iltimos avval tizimga kiring", "warning")
            return redirect(url_for('login', next=request.url))
        return f(*a,**kw)
    return deco

def admin_required(f):
    @wraps(f)
    def deco(*a,**kw):
        u = _me()
        if not u or not u['is_admin']:
            abort(403)
        return f(*a,**kw)
    return deco

def _me():
    if 'uid' in session:
        return get_db().execute("SELECT * FROM users WHERE id=?", (session['uid'],)).fetchone()
    return None

@app.context_processor
def _ctx():
    u = _me()
    unread = favs = 0
    if u:
        unread = get_db().execute("SELECT COUNT(*) FROM messages WHERE to_id=? AND is_read=0",(u['id'],)).fetchone()[0]
        favs   = get_db().execute("SELECT COUNT(*) FROM favorites WHERE user_id=?",(u['id'],)).fetchone()[0]
    return dict(me=u, unread=unread, fav_count=favs,
                animal_types=ANIMAL_TYPES, regions=REGIONS,
                now=datetime.now())

def fmt(v):
    try: return f"{int(v):,}".replace(',',' ')
    except: return str(v)
app.jinja_env.filters['fmt'] = fmt
app.jinja_env.filters['stars'] = lambda r: '⭐'*int(r or 5)+'☆'*(5-int(r or 5))
def from_json(v):
    try: import json; return json.loads(v or '[]')
    except: return []
app.jinja_env.filters['from_json'] = from_json

# ─── HOME ──────────────────────────────────────────────────────
@app.route('/')
def home():
    db = get_db()
    premium = db.execute("""SELECT l.*,u.full_name,u.rating,u.is_verified,u.username
        FROM listings l JOIN users u ON l.user_id=u.id
        WHERE l.is_active=1 AND l.is_sold=0 AND l.is_premium=1
        ORDER BY l.created_at DESC LIMIT 4""").fetchall()
    recent = db.execute("""SELECT l.*,u.full_name,u.rating,u.is_verified,u.username
        FROM listings l JOIN users u ON l.user_id=u.id
        WHERE l.is_active=1 AND l.is_sold=0
        ORDER BY l.created_at DESC LIMIT 8""").fetchall()
    stats = dict(
        listings = db.execute("SELECT COUNT(*) FROM listings WHERE is_active=1").fetchone()[0],
        users    = db.execute("SELECT COUNT(*) FROM users WHERE is_admin=0").fetchone()[0],
        sold     = db.execute("SELECT COUNT(*) FROM listings WHERE is_sold=1").fetchone()[0]+120,
        regions  = len(REGIONS),
    )
    top = db.execute("SELECT * FROM users WHERE is_admin=0 ORDER BY total_sales DESC LIMIT 4").fetchall()
    return render_template('main/home.html', premium=premium, recent=recent, stats=stats, top=top)

# ─── CATALOG ────────────────────────────────────────────────────
@app.route('/catalog')
def catalog():
    db   = get_db()
    q    = request.args.get('q','').strip()
    atype= request.args.get('type','')
    reg  = request.args.get('region','')
    minp = request.args.get('min','')
    maxp = request.args.get('max','')
    sort = request.args.get('sort','new')
    page = max(1,int(request.args.get('page','1') or 1))
    per  = 12

    sql  = """SELECT l.*,u.full_name,u.rating,u.is_verified,u.username
              FROM listings l JOIN users u ON l.user_id=u.id
              WHERE l.is_active=1 AND l.is_sold=0"""
    prm  = []
    if q:     sql+=" AND (l.title LIKE ? OR l.breed LIKE ? OR l.description LIKE ?)"; prm+=[f'%{q}%']*3
    if atype: sql+=" AND l.animal_slug=?"; prm.append(atype)
    if reg:   sql+=" AND l.region=?"; prm.append(reg)
    if minp:  sql+=" AND l.price>=?"; prm.append(int(minp))
    if maxp:  sql+=" AND l.price<=?"; prm.append(int(maxp))
    ord_map = {'new':'l.created_at DESC','price_asc':'l.price ASC',
               'price_desc':'l.price DESC','popular':'l.views DESC'}
    sql += f" ORDER BY l.is_premium DESC,{ord_map.get(sort,'l.created_at DESC')}"

    all_items = db.execute(sql,prm).fetchall()
    total = len(all_items)
    pages = max(1,(total+per-1)//per)
    items = all_items[(page-1)*per:page*per]
    return render_template('main/catalog.html', items=items, total=total,
                           pages=pages, page=page, q=q, atype=atype,
                           reg=reg, minp=minp, maxp=maxp, sort=sort)

# ─── DELIVERY CATALOG ────────────────────────────────────────────
UZBEKISTAN_DISTRICTS = {
    "Toshkent sh.": ["Yakkasaroy","Mirzo Ulug'bek","Yunusobod","Chilonzor","Uchtepa","Sergeli","Olmazor","Shayxontohur","Mirobod","Bektemir","Yashnobod","Zangiota"],
    "Toshkent vil.": ["Nurafshon","Olmaliq","Angren","Chirchiq","Bo'ka","Ohangaron","Parkent","Piskent","Qibray","Toshloq","Zangiota","Bostonliq","Orta Chirchiq","Yuqori Chirchiq","Quyi Chirchiq"],
    "Samarqand": ["Samarqand sh.","Urgut","Kattaqo'rg'on","Ishtixon","Jomboy","Payariq","Pastdarg'om","Oqdaryo","Bulungur","Narpay","Toyloq","Nurobod","Paxtachi","Qo'shrabot"],
    "Buxoro": ["Buxoro sh.","G'ijduvon","Kogon","Qorovulbozor","Romitan","Shofirkon","Vobkent","Jondor","Olot","Peshku","Qorako'l"],
    "Andijon": ["Andijon sh.","Asaka","Xonobod","Oltinko'l","Baliqchi","Bo'z","Buloqboshi","Izboskan","Jalaquduq","Ulug'nor","Marxamat","Paxtaobod","Qo'rg'ontepa","Shahrixon"],
    "Farg'ona": ["Farg'ona sh.","Marg'ilon","Qo'qon","Quva","Rishton","O'zbekiston","Dang'ara","Bag'dod","Beshariq","Buvayda","Furqat","Hamza","Oltiariq","Toshloq","Uchko'prik","Yozyovon"],
    "Namangan": ["Namangan sh.","Chortoq","Chust","Kosonsoy","Mingbuloq","Norin","Pop","To'raqo'rg'on","Uychi","Yangiqo'rg'on"],
    "Qashqadaryo": ["Qarshi sh.","Shahrisabz","G'uzor","Kasbi","Kitob","Ko'kdala","Mirishkor","Muborak","Nishon","Qamashi","Chiroqchi","Dehqonobod","Guzor","Yakkabog'"],
    "Surxondaryo": ["Termiz sh.","Boysun","Denov","Jarqo'rg'on","Qiziriq","Muzrabot","Oltinsoy","Sariosiyo","Sherobod","Shurchi","Uzun","Bandixon","Kumqo'rg'on","Angor"],
    "Xorazm": ["Urganch sh.","Xiva","Bog'ot","Gurlan","Hazorasp","Xonqa","Qo'shko'pir","Shovot","Tuproqqal'a","Yangiariq","Yangibozor"],
    "Navoiy": ["Navoiy sh.","Zarafshon","Karmana","Konimex","Nurota","Qiziltepa","Tomdi","Uchquduq","Xatirchi"],
    "Qoraqalpog'iston": ["Nukus sh.","Beruniy","Chimboy","Ellikkala","Kegeyli","Mo'ynoq","Qonliko'l","Qorao'zak","Shumanay","Taxtako'pir","To'rtko'l","Xo'jayli"],
}

@app.route('/delivery')
def delivery():
    db = get_db()
    region = request.args.get('region', '')
    district = request.args.get('district', '')
    q = request.args.get('q', '').strip()
    atype = request.args.get('type', '')
    page = max(1, int(request.args.get('page', '1') or 1))
    per = 12

    sql = """SELECT l.*,u.full_name,u.rating,u.is_verified,u.username
             FROM listings l JOIN users u ON l.user_id=u.id
             WHERE l.is_active=1 AND l.is_sold=0"""
    prm = []
    if q:       sql += " AND (l.title LIKE ? OR l.description LIKE ?)"; prm += [f'%{q}%']*2
    if atype:   sql += " AND l.animal_slug=?"; prm.append(atype)
    if region:  sql += " AND l.region=?"; prm.append(region)
    if district: sql += " AND l.district=?"; prm.append(district)
    sql += " ORDER BY l.is_premium DESC, l.created_at DESC"

    all_items = db.execute(sql, prm).fetchall()
    total = len(all_items)
    pages = max(1, (total + per - 1) // per)
    items = all_items[(page-1)*per:page*per]

    districts = UZBEKISTAN_DISTRICTS.get(region, []) if region else []

    return render_template('main/delivery.html',
                           items=items, total=total, pages=pages, page=page,
                           q=q, atype=atype, region=region, district=district,
                           regions=REGIONS, districts=districts,
                           all_districts=UZBEKISTAN_DISTRICTS,
                           animal_types=ANIMAL_TYPES)

# ─── LISTING DETAIL ─────────────────────────────────────────────
@app.route('/listing/<int:lid>')
def listing(lid):
    db = get_db()
    item = db.execute("""SELECT l.*,u.full_name,u.phone,u.rating,u.is_verified,
                                u.username,u.id as seller_id,u.bio,u.total_sales,u.avatar_letter
                         FROM listings l JOIN users u ON l.user_id=u.id WHERE l.id=?""",(lid,)).fetchone()
    if not item: abort(404)
    db.execute("UPDATE listings SET views=views+1 WHERE id=?",(lid,)); db.commit()
    related = db.execute("""SELECT l.*,u.full_name,u.rating,u.username
        FROM listings l JOIN users u ON l.user_id=u.id
        WHERE l.is_active=1 AND l.animal_slug=? AND l.id!=? AND l.is_sold=0
        ORDER BY l.views DESC LIMIT 3""",(item['animal_slug'],lid)).fetchall()
    seller_other = db.execute("""SELECT * FROM listings
        WHERE user_id=? AND is_active=1 AND id!=? AND is_sold=0 LIMIT 3""",
        (item['seller_id'],lid)).fetchall()
    is_fav = False
    if 'uid' in session:
        is_fav = bool(db.execute("SELECT 1 FROM favorites WHERE user_id=? AND listing_id=?",
                                 (session['uid'],lid)).fetchone())
    rev = db.execute("""SELECT r.*,u.full_name,u.username,u.avatar_letter FROM reviews r
        JOIN users u ON r.from_id=u.id WHERE r.to_id=? ORDER BY r.created_at DESC""",(item['seller_id'],)).fetchall()
    return render_template('main/listing.html', item=item, related=related,
                           seller_other=seller_other, is_fav=is_fav, reviews=rev,
                           delivery_persons=DELIVERY_PERSONS, vets=VETS)

# ─── DELIVERY REVIEW ────────────────────────────────────────────
@app.route('/delivery-review', methods=['POST'])
def delivery_review():
    if not session.get('uid'):
        flash('Iltimos tizimga kiring', 'error')
        return redirect('/login')
    pid  = request.form.get('person_id','')
    rat  = int(request.form.get('rating', 5))
    body = request.form.get('body','').strip()
    flash(f'✅ Yetkazib beruvchiga sharhingiz qabul qilindi! Reyting: {"⭐"*rat}', 'success')
    return redirect(request.referrer or '/catalog')

# ─── VET REVIEW ─────────────────────────────────────────────────
@app.route('/vet-review', methods=['POST'])
def vet_review():
    if not session.get('uid'):
        flash('Iltimos tizimga kiring', 'error')
        return redirect('/login')
    vid  = request.form.get('vet_id','')
    rat  = int(request.form.get('rating', 5))
    body = request.form.get('body','').strip()
    flash(f'✅ Veterinarga sharhingiz qabul qilindi! Reyting: {"⭐"*rat}', 'success')
    return redirect(request.referrer or '/catalog')

# ─── NEW LISTING ────────────────────────────────────────────────
@app.route('/listing/new', methods=['GET','POST'])
@login_required
def new_listing():
    if request.method == 'POST':
        db    = get_db()
        title = request.form.get('title','').strip()
        aslug = request.form.get('animal_slug','')
        price = int(request.form.get('price',0) or 0)
        region= request.form.get('region','')
        if not all([title,aslug,price,region]):
            flash("Barcha majburiy maydonlarni to'ldiring",'error')
            return render_template('main/new_listing.html', animal_types=ANIMAL_TYPES, regions=REGIONS)
        em = {s:e for s,e,_ in ANIMAL_TYPES}.get(aslug,'🐾')
        an = {s:n for s,_,n in ANIMAL_TYPES}.get(aslug,'')
        lat = request.form.get('latitude') or None
        lng = request.form.get('longitude') or None
        try: lat = float(lat) if lat else None
        except: lat = None
        try: lng = float(lng) if lng else None
        except: lng = None
        # Handle photos: up to 5 images as base64 JSON array
        import json as _json, base64 as _b64
        photos_b64 = []
        files = request.files.getlist('photos')
        for f in files[:5]:
            if f and f.filename:
                raw = f.read()
                if len(raw) < 8*1024*1024:  # max 8MB per file
                    mime = f.content_type or 'image/jpeg'
                    photos_b64.append('data:' + mime + ';base64,' + _b64.b64encode(raw).decode())
        photos_json = _json.dumps(photos_b64)
        db.execute("""INSERT INTO listings
            (user_id,title,animal_slug,animal_emoji,animal_name,price,region,
             district,age,gender,breed,count,weight,description,latitude,longitude,photos)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            session['uid'],title,aslug,em,an,price,region,
            request.form.get('district',''), request.form.get('age',''),
            request.form.get('gender',''), request.form.get('breed',''),
            int(request.form.get('count',1) or 1),
            request.form.get('weight',''), request.form.get('description','').strip(),
            lat, lng, photos_json,
        ))
        db.commit()
        lid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        flash("E'lon muvaffaqiyatli joylandi! 🎉",'success')
        return redirect(url_for('listing',lid=lid))
    return render_template('main/new_listing.html', animal_types=ANIMAL_TYPES, regions=REGIONS)

@app.route('/listing/<int:lid>/edit', methods=['GET','POST'])
@login_required
def edit_listing(lid):
    db   = get_db()
    item = db.execute("SELECT * FROM listings WHERE id=? AND user_id=?",(lid,session['uid'])).fetchone()
    if not item: abort(403)
    if request.method == 'POST':
        aslug = request.form.get('animal_slug', item['animal_slug'])
        em = {s:e for s,e,_ in ANIMAL_TYPES}.get(aslug,'🐾')
        an = {s:n for s,_,n in ANIMAL_TYPES}.get(aslug,'')
        db.execute("""UPDATE listings SET title=?,animal_slug=?,animal_emoji=?,animal_name=?,
                      price=?,region=?,district=?,age=?,gender=?,breed=?,count=?,weight=?,description=?
                      WHERE id=?""", (
            request.form.get('title',item['title']), aslug, em, an,
            int(request.form.get('price',item['price']) or 0),
            request.form.get('region',item['region']),
            request.form.get('district',''), request.form.get('age',''),
            request.form.get('gender',''), request.form.get('breed',''),
            int(request.form.get('count',1) or 1),
            request.form.get('weight',''), request.form.get('description','').strip(), lid,
        ))
        db.commit()
        flash("E'lon yangilandi ✅",'success')
        return redirect(url_for('listing',lid=lid))
    return render_template('main/edit_listing.html', item=item)

@app.route('/listing/<int:lid>/delete', methods=['POST'])
@login_required
def delete_listing(lid):
    db   = get_db()
    item = db.execute("SELECT * FROM listings WHERE id=?",(lid,)).fetchone()
    if not item: abort(404)
    u = _me()
    if item['user_id'] != session['uid'] and not u['is_admin']: abort(403)
    db.execute("DELETE FROM favorites WHERE listing_id=?",(lid,))
    db.execute("DELETE FROM listings WHERE id=?",(lid,))
    db.commit()
    flash("E'lon o'chirildi",'info')
    return redirect(url_for('my_listings') if item['user_id']==session['uid'] else url_for('admin_listings'))

@app.route('/listing/<int:lid>/sold', methods=['POST'])
@login_required
def mark_sold(lid):
    db = get_db()
    db.execute("UPDATE listings SET is_sold=1,is_active=0 WHERE id=? AND user_id=?",(lid,session['uid']))
    db.execute("UPDATE users SET total_sales=total_sales+1 WHERE id=?",(session['uid'],))
    db.commit()
    flash("E'lon 'Sotildi' deb belgilandi ✅",'success')
    return redirect(url_for('my_listings'))


# ─── BRON (RESERVATION) ─────────────────────────────────────────
@app.route('/listing/<int:lid>/bron', methods=['POST'])
@login_required
def bron_listing(lid):
    db = get_db()
    item = db.execute("SELECT * FROM listings WHERE id=?", (lid,)).fetchone()
    if not item: abort(404)
    if item['is_sold']:
        flash("Bu e'lon allaqachon sotilgan", 'error')
        return redirect(url_for('listing', lid=lid))
    if item['user_id'] == session['uid']:
        flash("O'z e'loningizni bron qila olmaysiz", 'error')
        return redirect(url_for('listing', lid=lid))
    if item['is_reserved']:
        if item['reserved_by'] == session['uid']:
            db.execute("UPDATE listings SET is_reserved=0,reserved_by=NULL,reserved_at=NULL WHERE id=?", (lid,))
            db.commit()
            flash("Bron bekor qilindi", 'info')
        else:
            flash("Bu e'lon allaqachon bronlangan", 'error')
        return redirect(url_for('listing', lid=lid))
    db.execute("UPDATE listings SET is_reserved=1,reserved_by=?,reserved_at=datetime('now') WHERE id=?",
               (session['uid'], lid))
    db.commit()
    flash("E'lon muvaffaqiyatli bronlandi! Muvaffaqiyatli bitimgacha saqlanadi.", 'success')
    return redirect(url_for('listing', lid=lid))

@app.route('/listing/<int:lid>/bron/cancel', methods=['POST'])
@login_required
def cancel_bron(lid):
    db = get_db()
    item = db.execute("SELECT * FROM listings WHERE id=?", (lid,)).fetchone()
    if not item: abort(404)
    me = _me()
    if item['reserved_by'] != session['uid'] and not me['is_admin']:
        abort(403)
    db.execute("UPDATE listings SET is_reserved=0,reserved_by=NULL,reserved_at=NULL WHERE id=?", (lid,))
    db.commit()
    flash("Bron bekor qilindi", 'info')
    return redirect(url_for('listing', lid=lid))

# ─── CLICK PAYMENT ───────────────────────────────────────────────
@app.route('/listing/<int:lid>/pay-click', methods=['POST'])
@login_required
def pay_click(lid):
    db = get_db()
    item = db.execute("SELECT * FROM listings WHERE id=?", (lid,)).fetchone()
    if not item: abort(404)
    return render_template('main/click_payment.html', item=item)

@app.route('/listing/<int:lid>/pay-click/confirm', methods=['POST'])
@login_required
def confirm_click_payment(lid):
    db = get_db()
    item = db.execute("SELECT * FROM listings WHERE id=?", (lid,)).fetchone()
    if not item: abort(404)
    db.execute("UPDATE listings SET is_sold=1,is_active=0,is_reserved=0 WHERE id=?", (lid,))
    db.execute("UPDATE users SET total_sales=total_sales+1 WHERE id=?", (item['user_id'],))
    db.commit()
    flash("💳 Click orqali to'lov muvaffaqiyatli amalga oshirildi!", 'success')
    return redirect(url_for('listing', lid=lid))

# ─── FAVORITES ──────────────────────────────────────────────────
@app.route('/favorites')
@login_required
def favorites():
    items = get_db().execute("""SELECT l.*,u.full_name,u.rating,u.username
        FROM favorites f JOIN listings l ON f.listing_id=l.id
        JOIN users u ON l.user_id=u.id
        WHERE f.user_id=? ORDER BY f.id DESC""",(session['uid'],)).fetchall()
    return render_template('main/favorites.html', items=items)

@app.route('/favorites/toggle/<int:lid>', methods=['POST'])
@login_required
def toggle_fav(lid):
    db = get_db()
    ex = db.execute("SELECT 1 FROM favorites WHERE user_id=? AND listing_id=?",
                    (session['uid'],lid)).fetchone()
    if ex:
        db.execute("DELETE FROM favorites WHERE user_id=? AND listing_id=?",(session['uid'],lid))
        action='removed'
    else:
        db.execute("INSERT OR IGNORE INTO favorites(user_id,listing_id) VALUES(?,?)",(session['uid'],lid))
        action='added'
    db.commit()
    cnt = db.execute("SELECT COUNT(*) FROM favorites WHERE user_id=?",(session['uid'],)).fetchone()[0]
    if request.headers.get('X-Requested-With')=='XMLHttpRequest':
        return jsonify({'action':action,'count':cnt})
    return redirect(request.referrer or url_for('favorites'))

# ─── MESSAGES ────────────────────────────────────────────────────
@app.route('/messages')
@login_required
def messages():
    db = get_db()
    convs = db.execute("""
        SELECT u.id,u.full_name,u.username,u.avatar_letter,
               MAX(m.created_at) as last_time,
               SUM(CASE WHEN m.to_id=? AND m.is_read=0 THEN 1 ELSE 0 END) as unread_cnt,
               (SELECT m2.body FROM messages m2
                WHERE (m2.from_id=u.id AND m2.to_id=?) OR (m2.from_id=? AND m2.to_id=u.id)
                ORDER BY m2.created_at DESC LIMIT 1) as last_msg
        FROM messages m
        JOIN users u ON (CASE WHEN m.from_id=? THEN m.to_id ELSE m.from_id END)=u.id
        WHERE m.from_id=? OR m.to_id=?
        GROUP BY u.id ORDER BY last_time DESC""",
        (session['uid'],session['uid'],session['uid'],
         session['uid'],session['uid'],session['uid'])).fetchall()
    return render_template('main/messages.html', convs=convs)

@app.route('/messages/<int:uid>', methods=['GET','POST'])
@login_required
def chat(uid):
    db    = get_db()
    other = db.execute("SELECT * FROM users WHERE id=?",(uid,)).fetchone()
    if not other: abort(404)
    if request.method == 'POST':
        body = request.form.get('body','').strip()
        lid  = request.form.get('listing_id') or None
        if body:
            db.execute("INSERT INTO messages(from_id,to_id,listing_id,body) VALUES(?,?,?,?)",
                       (session['uid'],uid,lid,body))
            db.commit()
        return redirect(url_for('chat',uid=uid))
    db.execute("UPDATE messages SET is_read=1 WHERE from_id=? AND to_id=?",(uid,session['uid']))
    db.commit()
    msgs = db.execute("""SELECT m.*,u.full_name,u.avatar_letter FROM messages m
        JOIN users u ON m.from_id=u.id
        WHERE (m.from_id=? AND m.to_id=?) OR (m.from_id=? AND m.to_id=?)
        ORDER BY m.created_at""",(session['uid'],uid,uid,session['uid'])).fetchall()
    lid = request.args.get('listing_id')
    listing_ref = get_db().execute("SELECT * FROM listings WHERE id=?",(lid,)).fetchone() if lid else None
    return render_template('main/chat.html', other=other, msgs=msgs, listing_ref=listing_ref)

# ─── PROFILE ─────────────────────────────────────────────────────
@app.route('/profile', methods=['GET','POST'])
@login_required
def profile():
    db = get_db()
    if request.method == 'POST':
        fn = request.form.get('full_name','').strip()
        db.execute("UPDATE users SET full_name=?,phone=?,region=?,email=?,bio=?,avatar_letter=? WHERE id=?",
                   (fn,
                    request.form.get('phone','').strip(),
                    request.form.get('region',''),
                    request.form.get('email','').strip(),
                    request.form.get('bio','').strip(),
                    fn[0].upper() if fn else '?',
                    session['uid']))
        op = request.form.get('old_password','')
        np = request.form.get('new_password','')
        if op and np:
            u = db.execute("SELECT * FROM users WHERE id=? AND password=?",
                           (session['uid'],hp(op))).fetchone()
            if u:
                db.execute("UPDATE users SET password=? WHERE id=?",(hp(np),session['uid']))
                flash("Parol o'zgartirildi ✅",'success')
            else:
                flash("Eski parol noto'g'ri",'error')
        db.commit()
        flash("Profil yangilandi ✅",'success')
        return redirect(url_for('profile'))
    user = db.execute("SELECT * FROM users WHERE id=?",(session['uid'],)).fetchone()
    return render_template('main/profile.html', user=user)

@app.route('/my-listings')
@login_required
def my_listings():
    items = get_db().execute("SELECT * FROM listings WHERE user_id=? ORDER BY created_at DESC",
                             (session['uid'],)).fetchall()
    return render_template('main/my_listings.html', items=items)

@app.route('/user/<username>')
def user_page(username):
    db   = get_db()
    user = db.execute("SELECT * FROM users WHERE username=?",(username,)).fetchone()
    if not user: abort(404)
    items = db.execute("""SELECT * FROM listings WHERE user_id=? AND is_active=1 AND is_sold=0
                          ORDER BY is_premium DESC,created_at DESC""",(user['id'],)).fetchall()
    revs  = db.execute("""SELECT r.*,u.full_name,u.username,u.avatar_letter FROM reviews r
        JOIN users u ON r.from_id=u.id WHERE r.to_id=? ORDER BY r.created_at DESC""",(user['id'],)).fetchall()
    avg   = db.execute("SELECT AVG(rating) FROM reviews WHERE to_id=?",(user['id'],)).fetchone()[0]
    return render_template('main/user.html', user=user, items=items,
                           reviews=revs, avg=round(avg or 5.0,1))

@app.route('/user/<int:uid>/review', methods=['POST'])
@login_required
def add_review(uid):
    db = get_db()
    rating = int(request.form.get('rating',5))
    body   = request.form.get('body','').strip()
    if uid == session['uid']:
        flash("O'zingizga baho bera olmaysiz",'error')
        return redirect(request.referrer or url_for('home'))
    db.execute("INSERT INTO reviews(from_id,to_id,rating,body) VALUES(?,?,?,?)",
               (session['uid'],uid,rating,body))
    avg = db.execute("SELECT AVG(rating) FROM reviews WHERE to_id=?",(uid,)).fetchone()[0]
    db.execute("UPDATE users SET rating=? WHERE id=?",(round(avg,1),uid))
    db.commit()
    flash("Sharh qo'shildi ✅",'success')
    return redirect(request.referrer or url_for('home'))

# ─── AUTH ─────────────────────────────────────────────────────────
@app.route('/login', methods=['GET','POST'])
def login():
    if 'uid' in session: return redirect(url_for('home'))
    if request.method == 'POST':
        uname = request.form.get('username','').strip()
        pwd   = request.form.get('password','').strip()
        user  = get_db().execute("SELECT * FROM users WHERE username=? AND password=?",
                                 (uname,hp(pwd))).fetchone()
        if user:
            session['uid'] = user['id']
            session.permanent = True
            flash(f"Xush kelibsiz, {user['full_name'] or user['username']}! 👋",'success')
            return redirect(request.args.get('next') or url_for('home'))
        flash("Login yoki parol noto'g'ri",'error')
    return render_template('main/login.html')

@app.route('/logout')
def logout():
    session.pop('uid',None)
    flash("Tizimdan chiqildi 👋",'info')
    return redirect(url_for('home'))

@app.route('/register', methods=['GET','POST'])
def register():
    if 'uid' in session: return redirect(url_for('home'))
    if request.method == 'POST':
        uname = request.form.get('username','').strip()
        fn    = request.form.get('full_name','').strip()
        phone = request.form.get('phone','').strip()
        reg   = request.form.get('region','')
        pwd   = request.form.get('password','').strip()
        pwd2  = request.form.get('password2','').strip()
        if not all([uname,fn,phone,reg,pwd]):
            flash("Barcha maydonlarni to'ldiring",'error')
        elif pwd != pwd2:
            flash("Parollar mos emas",'error')
        elif len(pwd) < 6:
            flash("Parol kamida 6 ta belgi",'error')
        elif get_db().execute("SELECT 1 FROM users WHERE username=?",(uname,)).fetchone():
            flash("Bu login band, boshqasini tanlang",'error')
        else:
            db = get_db()
            role = request.form.get('role','buyer')
            db.execute("INSERT INTO users(username,password,full_name,phone,region,avatar_letter,role) VALUES(?,?,?,?,?,?,?)",
                       (uname,hp(pwd),fn,phone,reg,fn[0].upper() if fn else '?',role))
            db.commit()
            uid = db.execute("SELECT id FROM users WHERE username=?",(uname,)).fetchone()[0]
            session['uid'] = uid
            flash(f"Xush kelibsiz, {fn}! Ro'yxatdan o'tdingiz 🎉",'success')
            return redirect(url_for('home'))
    return render_template('main/register.html')

# ─── SEARCH API ───────────────────────────────────────────────────
@app.route('/api/search')
def api_search():
    q = request.args.get('q','').strip()
    if len(q)<2: return jsonify([])
    r = get_db().execute("""SELECT id,title,animal_emoji,price,region FROM listings
        WHERE (title LIKE ? OR breed LIKE ?) AND is_active=1 AND is_sold=0 LIMIT 6""",
        (f'%{q}%',f'%{q}%')).fetchall()
    return jsonify([dict(id=x['id'],title=x['title'],emoji=x['animal_emoji'],
                         price=x['price'],region=x['region']) for x in r])

# ─── AI KATALOG ───────────────────────────────────────────────────
@app.route('/ai-catalog')
def ai_catalog():
    return render_template('main/ai_catalog.html', animal_types=ANIMAL_TYPES)

@app.route('/api/ai-animal-info', methods=['POST'])
def api_ai_animal_info():
    data = request.get_json(force=True)
    animal_slug  = data.get('animal_slug','')
    animal_name  = data.get('animal_name','')
    breed        = data.get('breed','')
    age          = data.get('age','')
    region       = data.get('region','')
    image_b64    = data.get('image_b64','')   # optional base64 image
    description  = data.get('description','')

    prompt_parts = [f"Hayvon turi: {animal_name}"]
    if breed:       prompt_parts.append(f"Zoti: {breed}")
    if age:         prompt_parts.append(f"Yoshi: {age}")
    if region:      prompt_parts.append(f"Mintaqa: {region}")
    if description: prompt_parts.append(f"Tavsif: {description}")

    system_msg = (
        "Sen O'zbekiston hayvonlar bozori uchun mutaxassis AI yordamchisisan. "
        "Foydalanuvchi hayvon haqida ma'lumot beradi va sen ularning hayvoni haqida "
        "quyidagi formatda JSON javob berishing kerak (faqat JSON, boshqa matn yo'q):\n"
        "{\n"
        '  "animal_info": "Hayvon haqida qisqacha ma\'lumot (2-3 gap)",\n'
        '  "breed_info": "Zot haqida ma\'lumot (agar ma\'lum bo\'lsa)",\n'
        '  "price_min": 500000,\n'
        '  "price_max": 2000000,\n'
        '  "price_avg": 1200000,\n'
        '  "price_explanation": "Narx nima asosida belgilangan",\n'
        '  "care_tips": ["Maslahat 1","Maslahat 2","Maslahat 3"],\n'
        '  "health_tips": ["Sog\'liq maslahat 1","Sog\'liq maslahat 2"],\n'
        '  "buy_tips": ["Sotib olish maslahat 1","Sotib olish maslahat 2"],\n'
        '  "confidence": 85\n'
        "}\n"
        "Narxlar O'zbekiston so'mida (UZS). Haqiqiy bozor narxlarini ko'rsating."
    )

    user_content = []
    if image_b64:
        # Strip data:image/...;base64, prefix if present
        if ',' in image_b64:
            image_b64 = image_b64.split(',',1)[1]
        user_content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": image_b64}
        })
    user_content.append({"type": "text", "text": "\n".join(prompt_parts)})

    import urllib.request as ur, json as js
    api_key = os.environ.get('ANTHROPIC_API_KEY', '') or _read_api_key()
    if not api_key:
        return jsonify({"ok": False, "error": "ANTHROPIC_API_KEY topilmadi"}), 500
    payload = js.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 1000,
        "system": system_msg,
        "messages": [{"role": "user", "content": user_content}]
    }).encode()
    req = ur.Request("https://api.anthropic.com/v1/messages",
        data=payload,
        headers={"Content-Type":"application/json",
                 "anthropic-version":"2023-06-01",
                 "x-api-key": api_key},
        method="POST")
    try:
        with ur.urlopen(req, timeout=30) as resp:
            result = js.loads(resp.read())
        raw = result['content'][0]['text']
        raw = raw.strip()
        if raw.startswith('```'): raw = raw.split('\n',1)[1].rsplit('```',1)[0]
        return jsonify({"ok": True, "data": js.loads(raw)})
    except ur.HTTPError as e:
        body = e.read().decode('utf-8', errors='ignore')
        return jsonify({"ok": False, "error": f"API xato {e.code}: {body}"}), 500
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ─── AI CHAT ──────────────────────────────────────────────────────
@app.route('/ai-chat')
def ai_chat():
    return render_template('main/ai_chat.html')

@app.route('/api/ai-chat', methods=['POST'])
def api_ai_chat():
    import urllib.request as ur, json as js, urllib.error as ue
    data = request.get_json(force=True) or {}
    messages = data.get('messages', [])
    if not messages:
        return jsonify({"ok": False, "error": "No messages"}), 400

    # Keep last 10 messages to avoid token overflow
    messages = messages[-10:]

    system_msg = (
        "Sen HayvonMarket platformasining AI yordamchisisisan. "
        "O'zbekistondagi qishloq xo'jaligi hayvonlari bo'yicha mutaxassissan: "
        "sigir, qo'y, echki, ot, tovuq, o'rdak, g'oz, quyon, tuya, cho'chqa, it, mushuk va boshqalar. "
        "Foydalanuvchilarga hayvonlar haqida: boqish, parvarishlash, kasallik va davolash, "
        "narxlar, sotib olish/sotish, zotlar, emlash, oziqlantirish, ko'paytirish bo'yicha maslahat berasan. "
        "Faqat hayvonlarga oid savollarga javob berasan. Boshqa mavzularda: "
        "'Men faqat hayvonlar haqida yordam bera olaman' deysan. "
        "Javoblarni qisqa, aniq va o'zbek tilida ber. Zarur bo'lsa ro'yxat ko'rinishida ber."
    )

    api_key = os.environ.get('ANTHROPIC_API_KEY', '') or _read_api_key()
    if not api_key:
        return jsonify({
            "ok": False,
            "error": "setup_required",
            "detail": "ANTHROPIC_API_KEY muhit o'zgaruvchisi yo'q. Railway/server sozlamalarida qo'shing."
        }), 500

    try:
        payload = js.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 1024,
            "system": system_msg,
            "messages": messages
        }).encode('utf-8')
        req = ur.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01",
                "x-api-key": api_key
            },
            method="POST"
        )
        with ur.urlopen(req, timeout=30) as resp:
            result = js.loads(resp.read())
        text = result['content'][0]['text']
        return jsonify({"ok": True, "reply": text})
    except ue.HTTPError as e:
        body = e.read().decode('utf-8', errors='ignore')
        try:
            err_json = js.loads(body)
            msg = err_json.get('error', {}).get('message', body)
        except Exception:
            msg = body[:300]
        return jsonify({"ok": False, "error": f"API {e.code}: {msg}"}), 500
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ─── GPS MAP ──────────────────────────────────────────────────────
@app.route('/gps-map')
def gps_map():
    db = get_db()
    listings = db.execute("""
        SELECT l.id, l.title, l.animal_emoji, l.price, l.region, l.district,
               l.latitude, l.longitude, u.username, u.full_name
        FROM listings l JOIN users u ON l.user_id=u.id
        WHERE l.is_active=1 AND l.is_sold=0
        ORDER BY l.created_at DESC
    """).fetchall()
    data = [dict(id=x['id'], title=x['title'], emoji=x['animal_emoji'],
                 price=x['price'], region=x['region'], district=x['district'],
                 lat=x['latitude'], lng=x['longitude'],
                 user=x['full_name'] or x['username']) for x in listings]
    return render_template('main/gps_map.html', listings_json=json.dumps(data))

@app.route('/api/listing/<int:lid>/set-location', methods=['POST'])
@login_required
def set_listing_location(lid):
    data = request.get_json(force=True)
    lat  = data.get('lat')
    lng  = data.get('lng')
    db   = get_db()
    listing = db.execute("SELECT * FROM listings WHERE id=?",(lid,)).fetchone()
    if not listing:
        return jsonify({"ok":False,"error":"Not found"}),404
    me = _me()
    if listing['user_id'] != me['id'] and not me['is_admin']:
        return jsonify({"ok":False,"error":"Forbidden"}),403
    db.execute("UPDATE listings SET latitude=?,longitude=? WHERE id=?",(lat,lng,lid))
    db.commit()
    return jsonify({"ok":True})

# ─── ABOUT / CONTACT ──────────────────────────────────────────────
@app.route('/about')
def about():
    return render_template('main/about.html')

@app.route('/contact')
def contact():
    return render_template('main/contact.html')

# ─── ADMIN ────────────────────────────────────────────────────────
@app.route('/admin/')
@login_required
@admin_required
def admin_index():
    db = get_db()
    stats = dict(
        users    = db.execute("SELECT COUNT(*) FROM users WHERE is_admin=0").fetchone()[0],
        listings = db.execute("SELECT COUNT(*) FROM listings").fetchone()[0],
        active   = db.execute("SELECT COUNT(*) FROM listings WHERE is_active=1").fetchone()[0],
        sold     = db.execute("SELECT COUNT(*) FROM listings WHERE is_sold=1").fetchone()[0],
        msgs     = db.execute("SELECT COUNT(*) FROM messages").fetchone()[0],
        reviews  = db.execute("SELECT COUNT(*) FROM reviews").fetchone()[0],
    )
    recent_users = db.execute("SELECT * FROM users ORDER BY created_at DESC LIMIT 8").fetchall()
    recent_listings = db.execute("""SELECT l.*,u.username FROM listings l JOIN users u ON l.user_id=u.id
        ORDER BY l.created_at DESC LIMIT 10""").fetchall()
    return render_template('admin/dashboard.html', stats=stats,
                           recent_users=recent_users, recent_listings=recent_listings)

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    users = get_db().execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    return render_template('admin/users.html', users=users)

@app.route('/admin/users/<int:uid>/verify', methods=['POST'])
@login_required
@admin_required
def admin_verify(uid):
    db = get_db()
    u  = db.execute("SELECT * FROM users WHERE id=?",(uid,)).fetchone()
    if u:
        db.execute("UPDATE users SET is_verified=? WHERE id=?",(0 if u['is_verified'] else 1,uid))
        db.commit()
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:uid>/delete', methods=['POST'])
@login_required
@admin_required
def admin_delete_user(uid):
    if uid == session['uid']:
        flash("O'zingizni o'chira olmaysiz",'error')
        return redirect(url_for('admin_users'))
    db = get_db()
    db.execute("DELETE FROM listings WHERE user_id=?",(uid,))
    db.execute("DELETE FROM messages WHERE from_id=? OR to_id=?",(uid,uid))
    db.execute("DELETE FROM favorites WHERE user_id=?",(uid,))
    db.execute("DELETE FROM reviews WHERE from_id=? OR to_id=?",(uid,uid))
    db.execute("DELETE FROM users WHERE id=?",(uid,))
    db.commit()
    flash("Foydalanuvchi o'chirildi",'info')
    return redirect(url_for('admin_users'))

@app.route('/admin/listings')
@login_required
@admin_required
def admin_listings():
    items = get_db().execute("""SELECT l.*,u.username,u.full_name FROM listings l
        JOIN users u ON l.user_id=u.id ORDER BY l.created_at DESC""").fetchall()
    return render_template('admin/listings.html', items=items)

@app.route('/admin/listings/<int:lid>/toggle', methods=['POST'])
@login_required
@admin_required
def admin_toggle_listing(lid):
    db = get_db()
    item = db.execute("SELECT * FROM listings WHERE id=?",(lid,)).fetchone()
    if item:
        db.execute("UPDATE listings SET is_active=?,is_premium=? WHERE id=?",
                   (0 if item['is_active'] else 1,
                    1 if request.form.get('premium') else item['is_premium'], lid))
        db.commit()
    return redirect(url_for('admin_listings'))

@app.route('/admin/listings/<int:lid>/delete', methods=['POST'])
@login_required
@admin_required
def admin_del_listing(lid):
    db = get_db()
    db.execute("DELETE FROM favorites WHERE listing_id=?",(lid,))
    db.execute("DELETE FROM listings WHERE id=?",(lid,))
    db.commit()
    flash("E'lon o'chirildi",'info')
    return redirect(url_for('admin_listings'))

# ─── ERROR HANDLERS ──────────────────────────────────────────────
@app.errorhandler(404)
def e404(e): return render_template('main/404.html'), 404
@app.errorhandler(403)
def e403(e): return render_template('main/403.html'), 403

# ─── RUN ─────────────────────────────────────────────────────────
# Always init DB on startup (needed for Railway/Gunicorn)
init_db()

if __name__=='__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    print("\n"+"═"*54)
    print("  🐄  HayvonMarket ishga tushdi!")
    print(f"  →  http://127.0.0.1:{port}")
    print("  →  Admin:  admin   / admin123")
    print("  →  Demo:   sardor  / demo123")
    print("═"*54+"\n")
    app.run(debug=debug, port=port, host='0.0.0.0')