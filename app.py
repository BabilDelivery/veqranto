from veqranto_final_center import register_final_center
from veqranto_master_ui import master_ui_register
from veqranto_master_features import register_master_features
import os, sqlite3, secrets, hashlib
from datetime import datetime, timedelta
from functools import wraps
from veqranto_hardening import register_hardening
from flask import Flask, request, redirect, session, jsonify, render_template_string, abort

BASE=os.path.dirname(os.path.abspath(__file__))
DB=os.path.join(BASE,"veqranto.db")

app=Flask(__name__)
register_hardening(app)
register_final_center(app)

master_ui_register(app)

# VEQRANTO MASTER FEATURES
register_master_features(app)

app.secret_key=os.environ.get("VEQRANTO_SECRET") or secrets.token_hex(32)

def db():
    c=sqlite3.connect(DB)
    c.row_factory=sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def init():
    c=db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS companies(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      slug TEXT UNIQUE NOT NULL,
      business_type TEXT DEFAULT 'متجر',
      phone TEXT DEFAULT '',
      address TEXT DEFAULT '',
      logo TEXT DEFAULT '',
      plan TEXT DEFAULT 'free',
      plan_until TEXT,
      active INTEGER DEFAULT 1,
      created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS users(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      company_id INTEGER NOT NULL,
      name TEXT NOT NULL,
      email TEXT UNIQUE NOT NULL,
      password TEXT NOT NULL,
      role TEXT DEFAULT 'owner',
      active INTEGER DEFAULT 1,
      created_at TEXT,
      FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS products(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      company_id INTEGER NOT NULL,
      name TEXT NOT NULL,
      sku TEXT DEFAULT '',
      category TEXT DEFAULT '',
      description TEXT DEFAULT '',
      image TEXT DEFAULT '',
      price REAL DEFAULT 0,
      cost REAL DEFAULT 0,
      stock INTEGER DEFAULT 0,
      min_stock INTEGER DEFAULT 0,
      active INTEGER DEFAULT 1,
      created_at TEXT,
      FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS customers(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      company_id INTEGER NOT NULL,
      name TEXT NOT NULL,
      phone TEXT DEFAULT '',
      address TEXT DEFAULT '',
      notes TEXT DEFAULT '',
      created_at TEXT,
      FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS orders(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      company_id INTEGER NOT NULL,
      customer_id INTEGER,
      invoice_no TEXT,
      total REAL DEFAULT 0,
      discount REAL DEFAULT 0,
      shipping REAL DEFAULT 0,
      payment TEXT DEFAULT 'cash',
      status TEXT DEFAULT 'new',
      notes TEXT DEFAULT '',
      created_at TEXT,
      FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS order_items(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      order_id INTEGER NOT NULL,
      product_id INTEGER NOT NULL,
      qty INTEGER DEFAULT 1,
      price REAL DEFAULT 0,
      FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE,
      FOREIGN KEY(product_id) REFERENCES products(id)
    );

    CREATE TABLE IF NOT EXISTS expenses(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      company_id INTEGER NOT NULL,
      title TEXT NOT NULL,
      amount REAL DEFAULT 0,
      category TEXT DEFAULT '',
      created_at TEXT,
      FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS staff_logs(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      company_id INTEGER NOT NULL,
      user_id INTEGER,
      action TEXT,
      created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS subscriptions(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      company_id INTEGER NOT NULL,
      plan TEXT,
      amount REAL DEFAULT 0,
      status TEXT DEFAULT 'active',
      start_date TEXT,
      end_date TEXT,
      created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS api_keys(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      company_id INTEGER NOT NULL,
      name TEXT,
      key_hash TEXT UNIQUE,
      prefix TEXT,
      active INTEGER DEFAULT 1,
      created_at TEXT,
      FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS categories(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      company_id INTEGER NOT NULL,
      name TEXT NOT NULL,
      created_at TEXT,
      UNIQUE(company_id,name)
    );
    """)
    c.commit()
    c.close()

init()

CSS="""
<style>
*{box-sizing:border-box}
body{margin:0;background:#070b12;color:#edf2f7;font-family:Arial,Tahoma,sans-serif}
a{text-decoration:none;color:inherit}
.top{height:64px;background:#0e1520;border-bottom:1px solid #202b39;display:flex;align-items:center;justify-content:space-between;padding:0 4%;position:sticky;top:0;z-index:5}
.logo{font-size:21px;font-weight:900}.logo i{color:#4ca4ff;font-style:normal}
.container{max-width:1250px;margin:auto;padding:22px 15px}
.nav{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:18px}
.nav a,.btn{background:#172131;padding:10px 14px;border-radius:9px;border:0;color:white;cursor:pointer;display:inline-block}
.btn{background:#287fff}.red{background:#b8344a}.green{background:#208b62}.yellow{background:#a97b18}
.card{background:#101824;border:1px solid #202c3c;border-radius:15px;padding:18px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px}
.stat{font-size:28px;font-weight:900;margin-top:7px}
.muted{color:#95a3b5}
.input,select,textarea{width:100%;padding:12px;background:#0a1019;color:white;border:1px solid #2b394b;border-radius:9px;margin:5px 0 12px}
textarea{min-height:90px;resize:vertical}
table{width:100%;border-collapse:collapse}
.table{overflow:auto}
td,th{padding:11px;border-bottom:1px solid #253142;text-align:right;white-space:nowrap}
.badge{display:inline-block;padding:5px 9px;border-radius:20px;background:#26354a;font-size:12px}
.alert{padding:12px;border-radius:10px;background:#18263a;margin-bottom:15px}
h1{margin-top:0}
.center{max-width:550px;margin:50px auto}
.hero{padding:45px 20px;text-align:center}
small{color:#8d9bae}
</style>
"""

def shell(title,body,**ctx):
    return render_template_string("""
    <!doctype html>
    <html lang="ar" dir="rtl">
    <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>VEQRANTO SaaS - {{title}}</title>
    """+CSS+"""
    </head>
    <body>
    <div class="top">
      <a class="logo" href="/">VEQRANTO <i>SaaS</i></a>
      {% if session.get('uid') %}
      <div>
        <span>{{session.get('name','')}}</span>
        &nbsp; <a href="/logout">خروج</a>
      </div>
      {% endif %}
    </div>
    <main class="container">
    {{body|safe}}
    </main>
    </body>
    </html>
    """,title=title,body=render_template_string(body,**ctx))

def current_user():
    if not session.get("uid"):
        return None
    c=db()
    u=c.execute("SELECT * FROM users WHERE id=? AND active=1",(session["uid"],)).fetchone()
    c.close()
    return u

def current_company():
    u=current_user()
    if not u:return None
    c=db()
    x=c.execute("SELECT * FROM companies WHERE id=? AND active=1",(u["company_id"],)).fetchone()
    c.close()
    return x

def login_required(f):
    @wraps(f)
    def w(*a,**kw):
        if not current_user():
            return redirect("/login")
        return f(*a,**kw)
    return w

def role_required(*roles):
    def deco(f):
        @wraps(f)
        def w(*a,**kw):
            u=current_user()
            if not u:return redirect("/login")
            if u["role"] not in roles:return abort(403)
            return f(*a,**kw)
        return w
    return deco

def log_action(action):
    u=current_user()
    if not u:return
    c=db()
    c.execute("INSERT INTO staff_logs(company_id,user_id,action,created_at) VALUES(?,?,?,?)",
              (u["company_id"],u["id"],action,now()))
    c.commit();c.close()

@app.route("/")
def home():
    return shell("الرئيسية","""
    <div class="card hero">
      <h1>VEQRANTO SaaS Builder</h1>
      <p class="muted">منصة واحدة لإنشاء وإدارة أنظمة الشركات والمتاجر والمطاعم والمكاتب والخدمات.</p>
      <br>
      <a class="btn" href="/register">إنشاء شركة</a>
      <a class="btn" href="/login">تسجيل الدخول</a>
    </div>
    <br>
    <div class="grid">
      <div class="card">🏪 <b>متجر</b><p class="muted">منتجات، مخزون، مبيعات.</p></div>
      <div class="card">🍔 <b>مطعم</b><p class="muted">أصناف وطلبات وفواتير.</p></div>
      <div class="card">💼 <b>خدمات</b><p class="muted">عملاء وفواتير ومصروفات.</p></div>
      <div class="card">📦 <b>مخزن</b><p class="muted">مخزون وحركة المنتجات.</p></div>
      <div class="card">👥 <b>موظفون</b><p class="muted">حسابات وصلاحيات.</p></div>
      <div class="card">🌐 <b>متجر عام</b><p class="muted">صفحة بيع خاصة بكل شركة.</p></div>
    </div>
    """)

REGISTER="""
<div class="center card">
<h1>إنشاء شركة</h1>
<form method="post">
<input class="input" name="name" placeholder="اسمك الكامل" required>
<input class="input" name="email" type="email" placeholder="البريد الإلكتروني" required>
<input class="input" name="company" placeholder="اسم الشركة / المتجر" required>
<input class="input" name="phone" placeholder="رقم الهاتف">
<select class="input" name="type">
<option>متجر</option><option>مطعم</option><option>صالون</option>
<option>مكتب</option><option>مخزن</option><option>خدمات</option>
</select>
<input class="input" name="password" type="password" placeholder="كلمة المرور" required>
<button class="btn">إنشاء الحساب</button>
</form></div>
"""

@app.route("/register",methods=["GET","POST"])
def register():
    if request.method=="POST":
        name=request.form["name"].strip()
        email=request.form["email"].strip().lower()
        company=request.form["company"].strip()
        phone=request.form.get("phone","").strip()
        typ=request.form.get("type","متجر")
        password=request.form["password"]
        if len(password)<6:
            return shell("تسجيل","<div class='alert'>كلمة المرور 6 أحرف على الأقل.</div>"+REGISTER)
        slug=secrets.token_hex(5)
        c=db()
        try:
            r=c.execute("""INSERT INTO companies
            (name,slug,business_type,phone,created_at,plan,plan_until)
            VALUES(?,?,?,?,?,?,?)""",
            (company,slug,typ,phone,now(),"free",(datetime.now()+timedelta(days=14)).strftime("%Y-%m-%d")))
            cid=r.lastrowid
            r=c.execute("""INSERT INTO users
            (company_id,name,email,password,role,created_at)
            VALUES(?,?,?,?,?,?)""",
            (cid,name,email,generate_hash(password),"owner",now()))
            uid=r.lastrowid
            c.execute("""INSERT INTO subscriptions
            (company_id,plan,amount,status,start_date,end_date,created_at)
            VALUES(?,?,?,?,?,?,?)""",
            (cid,"trial",0,"active",now(),(datetime.now()+timedelta(days=14)).strftime("%Y-%m-%d"),now()))
            c.commit()
            session["uid"]=uid
            session["name"]=name
            return redirect("/dashboard")
        except sqlite3.IntegrityError:
            c.rollback()
            return shell("تسجيل","<div class='alert'>الإيميل مستخدم مسبقاً.</div>"+REGISTER)
        finally:c.close()
    return shell("تسجيل",REGISTER)

LOGIN="""
<div class="center card">
<h1>تسجيل الدخول</h1>
<form method="post">
<input class="input" name="email" type="email" placeholder="البريد الإلكتروني" required>
<input class="input" name="password" type="password" placeholder="كلمة المرور" required>
<button class="btn">دخول</button>
</form>
</div>
"""

def generate_hash(x):
    from werkzeug.security import generate_password_hash
    return generate_password_hash(x)

def check_hash(h,x):
    from werkzeug.security import check_password_hash
    return check_password_hash(h,x)

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        c=db()
        u=c.execute("SELECT * FROM users WHERE email=? AND active=1",
                    (request.form["email"].strip().lower(),)).fetchone()
        c.close()
        if u and check_hash(u["password"],request.form["password"]):
            session["uid"]=u["id"]
            session["name"]=u["name"]
            return redirect("/dashboard")
        return shell("دخول","<div class='alert'>البريد أو كلمة المرور غير صحيحة.</div>"+LOGIN)
    return shell("دخول",LOGIN)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/dashboard")
@login_required
def dashboard():
    co=current_company()
    c=db();cid=co["id"]
    p=c.execute("SELECT COUNT(*) n FROM products WHERE company_id=? AND active=1",(cid,)).fetchone()["n"]
    stock=c.execute("SELECT COALESCE(SUM(stock),0) n FROM products WHERE company_id=?",(cid,)).fetchone()["n"]
    customers=c.execute("SELECT COUNT(*) n FROM customers WHERE company_id=?",(cid,)).fetchone()["n"]
    orders=c.execute("SELECT COUNT(*) n FROM orders WHERE company_id=?",(cid,)).fetchone()["n"]
    sales=c.execute("SELECT COALESCE(SUM(total),0) n FROM orders WHERE company_id=? AND status!='cancelled'",(cid,)).fetchone()["n"]
    expenses=c.execute("SELECT COALESCE(SUM(amount),0) n FROM expenses WHERE company_id=?",(cid,)).fetchone()["n"]
    low=c.execute("SELECT COUNT(*) n FROM products WHERE company_id=? AND stock<=min_stock AND active=1",(cid,)).fetchone()["n"]
    recent=c.execute("""SELECT orders.*,customers.name customer
      FROM orders LEFT JOIN customers ON customers.id=orders.customer_id
      WHERE orders.company_id=? ORDER BY orders.id DESC LIMIT 8""",(cid,)).fetchall()
    c.close()
    return shell("لوحة التحكم","""
    <h1>لوحة {{co.name}}</h1>
    <div class="nav">
      <a href="/products">📦 المنتجات</a>
      <a href="/customers">👥 العملاء</a>
      <a href="/orders">🧾 الطلبات</a>
      <a href="/new-order">➕ طلب جديد</a>
      <a href="/expenses">💸 المصروفات</a>
      <a href="/staff">👨‍💼 الموظفون</a>
      <a href="/reports">📊 التقارير</a>
      <a href="/subscription">💳 الاشتراك</a>
      <a href="/api-keys">🔑 API</a>
      <a href="/settings">⚙️ الإعدادات</a>
      <a href="/store/{{co.slug}}" target="_blank">🌐 المتجر</a>
    </div>
    <div class="grid">
      <div class="card">المنتجات<div class="stat">{{p}}</div></div>
      <div class="card">المخزون<div class="stat">{{stock}}</div></div>
      <div class="card">العملاء<div class="stat">{{customers}}</div></div>
      <div class="card">الطلبات<div class="stat">{{orders}}</div></div>
      <div class="card">المبيعات<div class="stat">{{"%.2f"|format(sales)}}</div></div>
      <div class="card">المصروفات<div class="stat">{{"%.2f"|format(expenses)}}</div></div>
      <div class="card">الصافي<div class="stat">{{"%.2f"|format(sales-expenses)}}</div></div>
      <div class="card">مخزون منخفض<div class="stat">{{low}}</div></div>
    </div>
    <br>
    <div class="card table"><h2>آخر الطلبات</h2>
    <table><tr><th>#</th><th>العميل</th><th>المبلغ</th><th>الحالة</th><th>التاريخ</th></tr>
    {% for x in recent %}
    <tr><td>{{x.id}}</td><td>{{x.customer or '-'}}</td><td>{{x.total}}</td><td><span class="badge">{{x.status}}</span></td><td>{{x.created_at}}</td></tr>
    {% endfor %}</table></div>
    """,co=co,p=p,stock=stock,customers=customers,orders=orders,sales=sales,expenses=expenses,low=low,recent=recent)

@app.route("/products",methods=["GET","POST"])
@login_required
def products():
    co=current_company();c=db()
    if request.method=="POST":
        sku=request.form.get("sku","").strip() or "SKU-"+secrets.token_hex(3).upper()
        c.execute("""INSERT INTO products
        (company_id,name,sku,category,description,image,price,cost,stock,min_stock,created_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (co["id"],request.form["name"],sku,request.form.get("category",""),
         request.form.get("description",""),request.form.get("image",""),
         float(request.form.get("price") or 0),float(request.form.get("cost") or 0),
         int(request.form.get("stock") or 0),int(request.form.get("min_stock") or 0),now()))
        c.commit();log_action("إضافة منتج")
    q=request.args.get("q","").strip()
    if q:
        rows=c.execute("""SELECT * FROM products WHERE company_id=? AND
        (name LIKE ? OR sku LIKE ? OR category LIKE ?) ORDER BY id DESC""",
        (co["id"],f"%{q}%",f"%{q}%",f"%{q}%")).fetchall()
    else:
        rows=c.execute("SELECT * FROM products WHERE company_id=? ORDER BY id DESC",(co["id"],)).fetchall()
    c.close()
    return shell("المنتجات","""
    <h1>📦 المنتجات</h1>
    <div class="card"><form method="post">
    <input class="input" name="name" placeholder="اسم المنتج" required>
    <input class="input" name="sku" placeholder="SKU اختياري">
    <input class="input" name="category" placeholder="التصنيف">
    <input class="input" name="description" placeholder="الوصف">
    <input class="input" name="image" placeholder="رابط الصورة">
    <input class="input" name="price" type="number" step="0.01" placeholder="سعر البيع">
    <input class="input" name="cost" type="number" step="0.01" placeholder="سعر التكلفة">
    <input class="input" name="stock" type="number" placeholder="المخزون">
    <input class="input" name="min_stock" type="number" placeholder="حد التنبيه">
    <button class="btn">إضافة المنتج</button>
    </form></div><br>
    <form><input class="input" name="q" value="{{q}}" placeholder="بحث عن منتج..."></form>
    <div class="card table"><table>
    <tr><th>المنتج</th><th>SKU</th><th>التصنيف</th><th>السعر</th><th>التكلفة</th><th>المخزون</th></tr>
    {% for x in rows %}<tr>
    <td>{{x.name}}</td><td>{{x.sku}}</td><td>{{x.category}}</td>
    <td>{{x.price}}</td><td>{{x.cost}}</td>
    <td>{% if x.stock<=x.min_stock %}<span class="badge">{{x.stock}} ⚠️</span>{% else %}{{x.stock}}{% endif %}</td>
    </tr>{% endfor %}
    </table></div>
    """,rows=rows,q=q)

@app.route("/customers",methods=["GET","POST"])
@login_required
def customers():
    co=current_company();c=db()
    if request.method=="POST":
        c.execute("""INSERT INTO customers(company_id,name,phone,address,notes,created_at)
        VALUES(?,?,?,?,?,?)""",(co["id"],request.form["name"],request.form.get("phone",""),
        request.form.get("address",""),request.form.get("notes",""),now()))
        c.commit();log_action("إضافة عميل")
    rows=c.execute("SELECT * FROM customers WHERE company_id=? ORDER BY id DESC",(co["id"],)).fetchall()
    c.close()
    return shell("العملاء","""
    <h1>👥 العملاء</h1>
    <div class="card"><form method="post">
    <input class="input" name="name" placeholder="اسم العميل" required>
    <input class="input" name="phone" placeholder="رقم الهاتف">
    <input class="input" name="address" placeholder="العنوان">
    <textarea name="notes" placeholder="ملاحظات"></textarea>
    <button class="btn">إضافة</button></form></div><br>
    <div class="card table"><table><tr><th>الاسم</th><th>الهاتف</th><th>العنوان</th><th>الملاحظات</th></tr>
    {% for x in rows %}<tr><td>{{x.name}}</td><td>{{x.phone}}</td><td>{{x.address}}</td><td>{{x.notes}}</td></tr>{% endfor %}
    </table></div>
    """,rows=rows)

@app.route("/new-order",methods=["GET","POST"])
@login_required
def new_order():
    co=current_company();c=db()
    customers=c.execute("SELECT * FROM customers WHERE company_id=? ORDER BY name",(co["id"],)).fetchall()
    products=c.execute("SELECT * FROM products WHERE company_id=? AND active=1 AND stock>0 ORDER BY name",(co["id"],)).fetchall()
    if request.method=="POST":
        customer_id=int(request.form["customer_id"])
        pid=int(request.form["product_id"])
        qty=max(1,int(request.form["qty"]))
        p=c.execute("SELECT * FROM products WHERE id=? AND company_id=?",(pid,co["id"])).fetchone()
        if not p or p["stock"]<qty:
            c.close()
            return shell("طلب","<div class='alert'>الكمية غير متوفرة.</div>"+ORDER_FORM,customers=customers,products=products)
        total=p["price"]*qty
        discount=float(request.form.get("discount") or 0)
        shipping=float(request.form.get("shipping") or 0)
        total=max(0,total-discount+shipping)
        inv="INV-"+datetime.now().strftime("%Y%m%d%H%M%S")+"-"+secrets.token_hex(2).upper()
        r=c.execute("""INSERT INTO orders
        (company_id,customer_id,invoice_no,total,discount,shipping,payment,status,notes,created_at)
        VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (co["id"],customer_id,inv,total,discount,shipping,request.form.get("payment","cash"),
         "new",request.form.get("notes",""),now()))
        oid=r.lastrowid
        c.execute("INSERT INTO order_items(order_id,product_id,qty,price) VALUES(?,?,?,?)",
                  (oid,pid,qty,p["price"]))
        c.execute("UPDATE products SET stock=stock-? WHERE id=?",(qty,pid))
        c.commit();c.close();log_action("إنشاء طلب")
        return redirect("/orders")
    c.close()
    return shell("طلب جديد",ORDER_FORM,customers=customers,products=products)

ORDER_FORM="""
<h1>➕ طلب جديد</h1>
<div class="card"><form method="post">
<select class="input" name="customer_id" required>
<option value="">اختر العميل</option>
{% for x in customers %}<option value="{{x.id}}">{{x.name}} — {{x.phone}}</option>{% endfor %}
</select>
<select class="input" name="product_id" required>
<option value="">اختر المنتج</option>
{% for x in products %}<option value="{{x.id}}">{{x.name}} — {{x.price}} — مخزون {{x.stock}}</option>{% endfor %}
</select>
<input class="input" name="qty" type="number" min="1" value="1" placeholder="الكمية">
<input class="input" name="discount" type="number" step="0.01" value="0" placeholder="الخصم">
<input class="input" name="shipping" type="number" step="0.01" value="0" placeholder="التوصيل">
<select class="input" name="payment"><option value="cash">نقدي</option><option value="cod">عند الاستلام</option><option value="card">بطاقة</option></select>
<textarea name="notes" placeholder="ملاحظات"></textarea>
<button class="btn">حفظ الطلب</button>
</form></div>
"""

@app.route("/orders")
@login_required
def orders():
    co=current_company();c=db()
    rows=c.execute("""SELECT o.*,c.name customer,c.phone
    FROM orders o LEFT JOIN customers c ON c.id=o.customer_id
    WHERE o.company_id=? ORDER BY o.id DESC""",(co["id"],)).fetchall()
    c.close()
    return shell("الطلبات","""
    <h1>🧾 الطلبات</h1><a class="btn" href="/new-order">➕ طلب جديد</a><br><br>
    <div class="card table"><table><tr><th>رقم</th><th>العميل</th><th>الهاتف</th><th>المبلغ</th><th>الدفع</th><th>الحالة</th><th>التاريخ</th></tr>
    {% for x in rows %}<tr>
    <td>{{x.invoice_no}}</td><td>{{x.customer or '-'}}</td><td>{{x.phone or '-'}}</td>
    <td>{{x.total}}</td><td>{{x.payment}}</td><td><span class="badge">{{x.status}}</span></td><td>{{x.created_at}}</td>
    </tr>{% endfor %}</table></div>
    """,rows=rows)

@app.route("/expenses",methods=["GET","POST"])
@login_required
def expenses():
    co=current_company();c=db()
    if request.method=="POST":
        c.execute("""INSERT INTO expenses(company_id,title,amount,category,created_at)
        VALUES(?,?,?,?,?)""",(co["id"],request.form["title"],float(request.form["amount"] or 0),
        request.form.get("category",""),now()))
        c.commit();log_action("إضافة مصروف")
    rows=c.execute("SELECT * FROM expenses WHERE company_id=? ORDER BY id DESC",(co["id"],)).fetchall()
    c.close()
    return shell("المصروفات","""
    <h1>💸 المصروفات</h1>
    <div class="card"><form method="post">
    <input class="input" name="title" placeholder="اسم المصروف" required>
    <input class="input" name="category" placeholder="التصنيف">
    <input class="input" name="amount" type="number" step="0.01" placeholder="المبلغ" required>
    <button class="btn">إضافة</button></form></div><br>
    <div class="card table"><table><tr><th>المصروف</th><th>التصنيف</th><th>المبلغ</th><th>التاريخ</th></tr>
    {% for x in rows %}<tr><td>{{x.title}}</td><td>{{x.category}}</td><td>{{x.amount}}</td><td>{{x.created_at}}</td></tr>{% endfor %}
    </table></div>
    """,rows=rows)

@app.route("/staff",methods=["GET","POST"])
@login_required
@role_required("owner","admin")
def staff():
    co=current_company();c=db()
    if request.method=="POST":
        try:
            c.execute("""INSERT INTO users(company_id,name,email,password,role,created_at)
            VALUES(?,?,?,?,?,?)""",
            (co["id"],request.form["name"],request.form["email"].lower(),
             generate_hash(request.form["password"]),request.form["role"],now()))
            c.commit();log_action("إضافة موظف")
        except sqlite3.IntegrityError:
            c.rollback()
    rows=c.execute("SELECT id,name,email,role,active,created_at FROM users WHERE company_id=? ORDER BY id",(co["id"],)).fetchall()
    c.close()
    return shell("الموظفون","""
    <h1>👨‍💼 الموظفون</h1>
    <div class="card"><form method="post">
    <input class="input" name="name" placeholder="اسم الموظف" required>
    <input class="input" name="email" type="email" placeholder="الإيميل" required>
    <input class="input" name="password" type="password" placeholder="كلمة المرور" required>
    <select class="input" name="role"><option value="staff">موظف</option><option value="admin">مدير</option></select>
    <button class="btn">إضافة موظف</button></form></div><br>
    <div class="card table"><table><tr><th>الاسم</th><th>الإيميل</th><th>الصلاحية</th><th>الحالة</th></tr>
    {% for x in rows %}<tr><td>{{x.name}}</td><td>{{x.email}}</td><td>{{x.role}}</td><td>{{'نشط' if x.active else 'متوقف'}}</td></tr>{% endfor %}
    </table></div>
    """,rows=rows)

@app.route("/reports")
@login_required
def reports():
    co=current_company();c=db();cid=co["id"]
    sales=c.execute("SELECT COALESCE(SUM(total),0) n FROM orders WHERE company_id=? AND status!='cancelled'",(cid,)).fetchone()["n"]
    expenses=c.execute("SELECT COALESCE(SUM(amount),0) n FROM expenses WHERE company_id=?",(cid,)).fetchone()["n"]
    orders=c.execute("SELECT COUNT(*) n FROM orders WHERE company_id=?",(cid,)).fetchone()["n"]
    products=c.execute("SELECT COUNT(*) n FROM products WHERE company_id=?",(cid,)).fetchone()["n"]
    top=c.execute("""SELECT p.name,SUM(i.qty) qty,SUM(i.qty*i.price) total
    FROM order_items i JOIN products p ON p.id=i.product_id
    JOIN orders o ON o.id=i.order_id WHERE o.company_id=?
    GROUP BY p.id ORDER BY qty DESC LIMIT 10""",(cid,)).fetchall()
    c.close()
    return shell("التقارير","""
    <h1>📊 التقارير</h1>
    <div class="grid">
      <div class="card">المبيعات<div class="stat">{{sales}}</div></div>
      <div class="card">المصروفات<div class="stat">{{expenses}}</div></div>
      <div class="card">الصافي<div class="stat">{{sales-expenses}}</div></div>
      <div class="card">عدد الطلبات<div class="stat">{{orders}}</div></div>
      <div class="card">عدد المنتجات<div class="stat">{{products}}</div></div>
    </div><br>
    <div class="card table"><h2>الأكثر مبيعاً</h2>
    <table><tr><th>المنتج</th><th>الكمية</th><th>الإجمالي</th></tr>
    {% for x in top %}<tr><td>{{x.name}}</td><td>{{x.qty}}</td><td>{{x.total}}</td></tr>{% endfor %}
    </table></div>
    """,sales=sales,expenses=expenses,orders=orders,products=products,top=top)

@app.route("/subscription")
@login_required
def subscription():
    co=current_company();c=db()
    rows=c.execute("SELECT * FROM subscriptions WHERE company_id=? ORDER BY id DESC",(co["id"],)).fetchall()
    c.close()
    return shell("الاشتراك","""
    <h1>💳 الاشتراك</h1>
    <div class="card">
      <h2>الخطة الحالية: {{co.plan}}</h2>
      <p>تنتهي: {{co.plan_until or 'غير محدد'}}</p>
      <p class="muted">النظام مجهز لخطط مجانية وتجريبية ومدفوعة، ويمكن ربط بوابة الدفع لاحقاً.</p>
    </div><br>
    <div class="grid">
      <div class="card"><h2>Free</h2><p>للشروع والتجربة.</p></div>
      <div class="card"><h2>Pro</h2><p>للشركات الصغيرة.</p></div>
      <div class="card"><h2>Business</h2><p>للشركات المتعددة الموظفين.</p></div>
    </div>
    """,co=co,rows=rows)

@app.route("/api-keys",methods=["GET","POST"])
@login_required
@role_required("owner","admin")
def api_keys():
    co=current_company();c=db()
    created=None
    if request.method=="POST":
        raw="vqr_"+secrets.token_urlsafe(32)
        h=hashlib.sha256(raw.encode()).hexdigest()
        prefix=raw[:12]
        c.execute("""INSERT INTO api_keys(company_id,name,key_hash,prefix,created_at)
        VALUES(?,?,?,?,?)""",(co["id"],request.form.get("name","API"),h,prefix,now()))
        c.commit()
        created=raw
    rows=c.execute("SELECT id,name,prefix,active,created_at FROM api_keys WHERE company_id=?",(co["id"],)).fetchall()
    c.close()
    return shell("API","""
    <h1>🔑 API Keys</h1>
    {% if created %}
    <div class="alert">احفظ المفتاح الآن، لن يظهر كاملاً مرة ثانية:<br><b>{{created}}</b></div>
    {% endif %}
    <div class="card"><form method="post">
    <input class="input" name="name" placeholder="اسم المفتاح">
    <button class="btn">إنشاء API Key</button></form></div><br>
    <div class="card table"><table><tr><th>الاسم</th><th>البادئة</th><th>الحالة</th><th>التاريخ</th></tr>
    {% for x in rows %}<tr><td>{{x.name}}</td><td>{{x.prefix}}...</td><td>{{'نشط' if x.active else 'متوقف'}}</td><td>{{x.created_at}}</td></tr>{% endfor %}
    </table></div>
    """,rows=rows,created=created)

@app.route("/settings",methods=["GET","POST"])
@login_required
def settings():
    co=current_company()

    if request.method=="POST":
        c=db()
        name=request.form.get("name","").strip()
        phone=request.form.get("phone","").strip()
        address=request.form.get("address","").strip()
        business_type=request.form.get("type","متجر").strip()
        logo=request.form.get("logo","").strip()

        if not name:
            name=co["name"]

        c.execute("""
            UPDATE companies
            SET name=?,phone=?,address=?,business_type=?,logo=?
            WHERE id=?
        """,(name,phone,address,business_type,logo,co["id"]))

        c.commit()
        c.close()
        log_action("تعديل هوية وإعدادات الشركة")
        return redirect("/settings")

    return shell("هوية الشركة","""
    <style>
      .brand-preview{
        display:flex;
        align-items:center;
        gap:16px;
        padding:18px;
        border:1px solid #eee;
        border-radius:16px;
        margin-bottom:18px;
        background:#fafafa;
      }
      .brand-logo{
        width:72px;
        height:72px;
        border-radius:18px;
        object-fit:cover;
        background:#111827;
        display:flex;
        align-items:center;
        justify-content:center;
        color:white;
        font-size:28px;
        font-weight:900;
      }
      .hint{
        color:#777;
        font-size:13px;
        margin-top:-7px;
        margin-bottom:14px;
      }
    </style>

    <h1>🎨 هوية الشركة</h1>
    <p class="muted">تحكم باسم شركتك وشعارها ومعلومات التواصل التي تظهر في النظام والمتجر العام.</p>

    <div class="card">
      <div class="brand-preview">
        {% if co.logo %}
          <img class="brand-logo" src="{{co.logo}}" alt="شعار {{co.name}}">
        {% else %}
          <div class="brand-logo">{{co.name[:1]}}</div>
        {% endif %}
        <div>
          <h2 style="margin:0">{{co.name}}</h2>
          <div class="muted">{{co.business_type}}</div>
          {% if co.phone %}<div>{{co.phone}}</div>{% endif %}
        </div>
      </div>

      <form method="post">

        <label>اسم الشركة / المتجر</label>
        <input class="input" name="name"
               value="{{co.name}}"
               placeholder="اسم الشركة">

        <label>رابط الشعار</label>
        <input class="input" name="logo"
               value="{{co.logo or ''}}"
               placeholder="https://example.com/logo.png">

        <div class="hint">
          استخدم رابط صورة مباشر للشعار PNG أو JPG أو WEBP.
        </div>

        <label>رقم الهاتف</label>
        <input class="input" name="phone"
               value="{{co.phone or ''}}"
               placeholder="07xxxxxxxxx">

        <label>العنوان</label>
        <input class="input" name="address"
               value="{{co.address or ''}}"
               placeholder="العنوان">

        <label>نوع النشاط</label>
        <select class="input" name="type">
          {% for x in ['متجر','مطعم','صالون','مكتب','مخزن','خدمات'] %}
          <option {% if x==co.business_type %}selected{% endif %}>{{x}}</option>
          {% endfor %}
        </select>

        <button class="btn" type="submit">
          💾 حفظ هوية الشركة
        </button>

      </form>
    </div>
    """,co=co)

@app.route("/store/<slug>")
def store(slug):
    c=db()
    co=c.execute("SELECT * FROM companies WHERE slug=? AND active=1",(slug,)).fetchone()
    if not co:abort(404)
    products=c.execute("SELECT * FROM products WHERE company_id=? AND active=1 AND stock>0 ORDER BY id DESC",(co["id"],)).fetchall()
    c.close()
    return shell(co["name"],"""
    <div class="card hero">
      {% if co.logo %}<img src="{{co.logo}}" style="max-width:120px"><br>{% endif %}
      <h1>{{co.name}}</h1><p class="muted">{{co.business_type}}</p>
      <small>{{co.address}} {{co.phone}}</small>
    </div><br>
    <div class="grid">
    {% for x in products %}
      <div class="card">
        {% if x.image %}<img src="{{x.image}}" style="width:100%;height:160px;object-fit:cover;border-radius:10px"><br>{% endif %}
        <h3>{{x.name}}</h3>
        <small>{{x.category}}</small>
        <p>{{x.description}}</p>
        <b>{{x.price}}</b>
        <br><br><span class="badge">متوفر</span>
      </div>
    {% endfor %}
    </div>
    """,co=co,products=products)

def api_auth():
    auth=request.headers.get("Authorization","")
    if not auth.startswith("Bearer "):
        return None
    raw=auth[7:].strip()
    h=hashlib.sha256(raw.encode()).hexdigest()
    c=db()
    x=c.execute("""SELECT company_id FROM api_keys
    WHERE key_hash=? AND active=1""",(h,)).fetchone()
    c.close()
    return x["company_id"] if x else None

@app.route("/api/health")
def health():
    return jsonify(ok=True,service="VEQRANTO SaaS",version="3.0")

@app.route("/api/company")
def api_company():
    cid=api_auth()
    if not cid:return jsonify(ok=False,error="unauthorized"),401
    c=db();x=c.execute("SELECT id,name,slug,business_type,phone,address,plan FROM companies WHERE id=?",(cid,)).fetchone();c.close()
    return jsonify(ok=True,company=dict(x))

@app.route("/api/products")
def api_products():
    cid=api_auth()
    if not cid:return jsonify(ok=False,error="unauthorized"),401
    c=db();rows=c.execute("""SELECT id,name,sku,category,description,image,
    price,cost,stock,min_stock FROM products WHERE company_id=? AND active=1""",(cid,)).fetchall();c.close()
    return jsonify(ok=True,count=len(rows),products=[dict(x) for x in rows])

@app.route("/api/customers")
def api_customers():
    cid=api_auth()
    if not cid:return jsonify(ok=False,error="unauthorized"),401
    c=db();rows=c.execute("SELECT * FROM customers WHERE company_id=? ORDER BY id DESC",(cid,)).fetchall();c.close()
    return jsonify(ok=True,customers=[dict(x) for x in rows])

@app.route("/api/orders")
def api_orders():
    cid=api_auth()
    if not cid:return jsonify(ok=False,error="unauthorized"),401
    c=db();rows=c.execute("""SELECT id,invoice_no,customer_id,total,discount,shipping,
    payment,status,notes,created_at FROM orders WHERE company_id=? ORDER BY id DESC""",(cid,)).fetchall();c.close()
    return jsonify(ok=True,orders=[dict(x) for x in rows])

@app.route("/api/order",methods=["POST"])
def api_order():
    cid=api_auth()
    if not cid:return jsonify(ok=False,error="unauthorized"),401
    data=request.get_json(silent=True) or {}
    customer=data.get("customer_id")
    items=data.get("items") or []
    if not customer or not items:
        return jsonify(ok=False,error="customer_id and items required"),400
    c=db()
    cu=c.execute("SELECT * FROM customers WHERE id=? AND company_id=?",(customer,cid)).fetchone()
    if not cu:
        c.close();return jsonify(ok=False,error="customer_not_found"),404
    total=0;prepared=[]
    for item in items:
        p=c.execute("SELECT * FROM products WHERE id=? AND company_id=? AND active=1",(item.get("product_id"),cid)).fetchone()
        qty=int(item.get("qty",1))
        if not p or qty<1 or p["stock"]<qty:
            c.close();return jsonify(ok=False,error="product_or_stock_error",product_id=item.get("product_id")),400
        total+=p["price"]*qty
        prepared.append((p,qty))
    discount=float(data.get("discount",0) or 0)
    shipping=float(data.get("shipping",0) or 0)
    total=max(0,total-discount+shipping)
    inv="API-"+datetime.now().strftime("%Y%m%d%H%M%S")+"-"+secrets.token_hex(2).upper()
    r=c.execute("""INSERT INTO orders(company_id,customer_id,invoice_no,total,discount,shipping,
    payment,status,notes,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)""",
    (cid,customer,inv,total,discount,shipping,data.get("payment","cash"),"new",data.get("notes",""),now()))
    oid=r.lastrowid
    for p,qty in prepared:
        c.execute("INSERT INTO order_items(order_id,product_id,qty,price) VALUES(?,?,?,?)",(oid,p["id"],qty,p["price"]))
        c.execute("UPDATE products SET stock=stock-? WHERE id=?",(qty,p["id"]))
    c.commit();c.close()
    return jsonify(ok=True,order_id=oid,invoice_no=inv,total=total,status="new")

@app.route("/api/order/<int:oid>",methods=["GET"])
def api_order_get(oid):
    cid=api_auth()
    if not cid:return jsonify(ok=False,error="unauthorized"),401
    c=db()
    o=c.execute("SELECT * FROM orders WHERE id=? AND company_id=?",(oid,cid)).fetchone()
    if not o:c.close();return jsonify(ok=False,error="not_found"),404
    items=c.execute("""SELECT oi.*,p.name FROM order_items oi JOIN products p ON p.id=oi.product_id
    WHERE oi.order_id=?""",(oid,)).fetchall()
    c.close()
    return jsonify(ok=True,order=dict(o),items=[dict(x) for x in items])

@app.errorhandler(403)
def forbidden(e):
    return shell("403","<div class='card'><h1>403</h1><p>ليس لديك صلاحية لهذه الصفحة.</p></div>"),403

@app.errorhandler(404)
def notfound(e):
    return shell("404","<div class='card'><h1>404</h1><p>الصفحة غير موجودة.</p></div>"),404


if __name__=="__main__":
    print("="*55)
    print("VEQRANTO SaaS v3.0")
    print("http://127.0.0.1:5050")
    print("http://0.0.0.0:5050")
    print("="*55)
    



# VEQRANTO v3 bootstrap
import sys
sys.modules["app"] = sys.modules[__name__]

# VEQRANTO V3 EXTENSIONS
import sys
sys.modules["app"] = sys.modules[__name__]

import upgrade
import upgrade2

# VEQRANTO MASTER FEATURES
if __name__ == "__main__":
    app.run(host="0.0.0.0",port=5050,debug=False)
