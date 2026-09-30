
from flask import render_template_string, session, redirect
import sqlite3
from pathlib import Path

DB_FILE=str(Path(__file__).resolve().parent/"veqranto.db")

def _db():
    c=sqlite3.connect(DB_FILE)
    c.row_factory=sqlite3.Row
    return c

def _user():
    uid=session.get("user_id")
    if not uid:
        return None
    c=_db()
    u=c.execute("""
      SELECT u.*,c.name company_name,c.slug company_slug
      FROM users u LEFT JOIN companies c ON c.id=u.company_id
      WHERE u.id=?
    """,(uid,)).fetchone()
    c.close()
    return u

def _count(c,t,cid):
    try:
        return c.execute(
            f"SELECT COUNT(*) FROM {t} WHERE company_id=?",(cid,)
        ).fetchone()[0]
    except:
        return 0

def register_final_center(app):

    @app.route("/veqranto")
    def veqranto_master_center():
        u=_user()
        if not u:
            return redirect("/login")

        cid=u["company_id"]
        c=_db()

        data={
          "products":_count(c,"products",cid),
          "customers":_count(c,"customers",cid),
          "orders":_count(c,"orders",cid),
          "expenses":_count(c,"expenses",cid),
          "coupons":_count(c,"coupons",cid),
          "inventory":_count(c,"inventory_movements",cid),
          "notifications":_count(c,"notifications",cid)
        }

        try:
            data["sales"]=c.execute(
              "SELECT COALESCE(SUM(total),0) FROM orders WHERE company_id=?",
              (cid,)
            ).fetchone()[0] or 0
        except:
            data["sales"]=0

        try:
            data["expense_total"]=c.execute(
              "SELECT COALESCE(SUM(amount),0) FROM expenses WHERE company_id=?",
              (cid,)
            ).fetchone()[0] or 0
        except:
            data["expense_total"]=0

        try:
            data["low_stock"]=c.execute("""
              SELECT COUNT(*) FROM products
              WHERE company_id=?
              AND COALESCE(stock,0)<=COALESCE(low_stock,5)
            """,(cid,)).fetchone()[0]
        except:
            data["low_stock"]=0

        c.close()

        return render_template_string("""
<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>VEQRANTO</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#070a10;color:#eef2f7;font-family:Arial,sans-serif}
header{background:#101722;border-bottom:1px solid #273243;padding:22px}
.wrap{max-width:1250px;margin:auto;padding:20px}
.brand{font-size:27px;font-weight:800}
.muted{color:#8995a6}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px}
.card{background:#101722;border:1px solid #263244;border-radius:17px;padding:20px}
.number{font-size:30px;font-weight:800;margin-top:8px}
.menu{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-top:15px}
a{display:block;text-decoration:none;color:#eef2f7}
.btn{background:#141e2c;border:1px solid #29384d;padding:16px;border-radius:14px}
.btn:hover{background:#1b283a}
h2{margin-top:30px}
.warn{border-color:#80531d}
</style>
</head>
<body>
<header>
<div class="wrap">
<div class="brand">VEQRANTO MASTER</div>
<div class="muted">{{u["company_name"] or "VEQRANTO"}} — النظام المركزي</div>
</div>
</header>

<main class="wrap">

<div class="grid">
<div class="card">المنتجات<div class="number">{{d.products}}</div></div>
<div class="card">العملاء<div class="number">{{d.customers}}</div></div>
<div class="card">الطلبات<div class="number">{{d.orders}}</div></div>
<div class="card">المصاريف<div class="number">{{d.expenses}}</div></div>
<div class="card">الكوبونات<div class="number">{{d.coupons}}</div></div>
<div class="card">حركات المخزون<div class="number">{{d.inventory}}</div></div>
<div class="card">الإشعارات<div class="number">{{d.notifications}}</div></div>
<div class="card {% if d.low_stock %}warn{% endif %}">
منخفض المخزون<div class="number">{{d.low_stock}}</div>
</div>
<div class="card">إجمالي المبيعات<div class="number">{{d.sales}}</div></div>
<div class="card">إجمالي المصاريف<div class="number">{{d.expense_total}}</div></div>
</div>

<h2>الإدارة</h2>
<div class="menu">
<a class="btn" href="/dashboard">📊 لوحة التحكم</a>
<a class="btn" href="/products">📦 المنتجات</a>
<a class="btn" href="/customers">👥 العملاء</a>
<a class="btn" href="/orders">🧾 الطلبات</a>
<a class="btn" href="/new-order">➕ طلب جديد</a>
<a class="btn" href="/expenses">💰 المصاريف</a>
<a class="btn" href="/staff">👤 الموظفون</a>
<a class="btn" href="/reports">📈 التقارير</a>
<a class="btn" href="/subscription">💳 الاشتراك</a>
<a class="btn" href="/api-keys">🔑 API</a>
<a class="btn" href="/settings">⚙️ الإعدادات</a>
<a class="btn" href="/store/{{u["company_slug"] or "veqranto"}}">🛒 المتجر</a>
<a class="btn" href="/master">🛠 Master</a>
</div>

<h2>الـMaster API</h2>
<div class="menu">
<a class="btn" href="/api/master/dashboard">Dashboard API</a>
<a class="btn" href="/api/master/settings">Settings API</a>
<a class="btn" href="/api/master/inventory">Inventory API</a>
<a class="btn" href="/api/master/coupons">Coupons API</a>
<a class="btn" href="/api/master/audit">Audit API</a>
<a class="btn" href="/api/master/report">Reports API</a>
</div>

<div class="card" style="margin-top:25px">
<b>VEQRANTO SaaS v3.0</b>
<div class="muted">Company ID: {{u["company_id"]}}</div>
<div class="muted">كل بيانات اللوحة مربوطة بالشركة الحالية.</div>
</div>

</main>
</body>
</html>
""",u=u,d=data)

