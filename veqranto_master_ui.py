
from flask import render_template_string, session, redirect, url_for
import sqlite3
from pathlib import Path

DB_FILE = str(Path(__file__).resolve().parent / "veqranto.db")

def master_ui_db():
    c=sqlite3.connect(DB_FILE)
    c.row_factory=sqlite3.Row
    return c

def master_ui_user():
    uid=session.get("user_id")
    if not uid:
        return None
    c=master_ui_db()
    x=c.execute("""
        SELECT u.*, c.name AS company_name, c.slug AS company_slug
        FROM users u
        LEFT JOIN companies c ON c.id=u.company_id
        WHERE u.id=?
    """,(uid,)).fetchone()
    c.close()
    return x

def master_ui_register(app):

    @app.route("/master-center")
    def master_center_ui():
        u=master_ui_user()
        if not u:
            return redirect("/login")

        cid=u["company_id"]

        c=master_ui_db()

        def count(table, where="company_id=?"):
            try:
                return c.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE {where}",
                    (cid,)
                ).fetchone()[0]
            except:
                return 0

        def total(table, field="amount"):
            try:
                x=c.execute(
                    f"SELECT COALESCE(SUM({field}),0) FROM {table} WHERE company_id=?",
                    (cid,)
                ).fetchone()[0]
                return x or 0
            except:
                return 0

        data={
            "products":count("products"),
            "customers":count("customers"),
            "orders":count("orders"),
            "expenses":count("expenses"),
            "staff":count("users"),
            "notifications":count("notifications"),
            "coupons":count("coupons"),
            "inventory":count("inventory_movements"),
            "sales":total("orders"),
            "expense_total":total("expenses"),
        }

        try:
            low=c.execute("""
                SELECT COUNT(*) FROM products
                WHERE company_id=?
                AND COALESCE(stock,0)<=COALESCE(low_stock,5)
            """,(cid,)).fetchone()[0]
        except:
            low=0

        data["low_stock"]=low
        c.close()

        return render_template_string("""
<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>VEQRANTO MASTER</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#080b12;color:#edf2f7;font-family:Arial,sans-serif}
a{text-decoration:none;color:inherit}
.top{padding:20px;background:#101622;border-bottom:1px solid #202938}
.brand{font-size:25px;font-weight:800}
.sub{color:#8e9aaa;margin-top:5px}
.wrap{max-width:1250px;margin:auto;padding:20px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px}
.card{background:#101722;border:1px solid #202938;border-radius:16px;padding:20px}
.num{font-size:30px;font-weight:800;margin-top:10px}
.label{color:#9ba7b7}
.nav{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:22px 0}
.btn{background:#151e2d;border:1px solid #29364a;padding:16px;border-radius:13px}
.btn:hover{background:#1c2839}
.warn{border-color:#754d20}
.title{margin:28px 0 12px}
small{color:#8491a3}
</style>
</head>
<body>
<div class="top">
<div class="wrap">
<div class="brand">VEQRANTO MASTER</div>
<div class="sub">{{u["company_name"] or "VEQRANTO"}} — لوحة التحكم المركزية</div>
</div>
</div>

<div class="wrap">

<div class="grid">
<div class="card"><div class="label">المنتجات</div><div class="num">{{data.products}}</div></div>
<div class="card"><div class="label">العملاء</div><div class="num">{{data.customers}}</div></div>
<div class="card"><div class="label">الطلبات</div><div class="num">{{data.orders}}</div></div>
<div class="card"><div class="label">الموظفون</div><div class="num">{{data.staff}}</div></div>
<div class="card"><div class="label">المصاريف</div><div class="num">{{data.expenses}}</div></div>
<div class="card"><div class="label">الكوبونات</div><div class="num">{{data.coupons}}</div></div>
<div class="card"><div class="label">حركات المخزون</div><div class="num">{{data.inventory}}</div></div>
<div class="card {% if data.low_stock %}warn{% endif %}">
<div class="label">منخفض المخزون</div>
<div class="num">{{data.low_stock}}</div>
</div>
</div>

<h2 class="title">إدارة النظام</h2>
<div class="nav">
<a class="btn" href="/dashboard">📊 Dashboard</a>
<a class="btn" href="/products">📦 المنتجات</a>
<a class="btn" href="/customers">👥 العملاء</a>
<a class="btn" href="/orders">🧾 الطلبات</a>
<a class="btn" href="/new-order">➕ طلب جديد</a>
<a class="btn" href="/expenses">💰 المصاريف</a>
<a class="btn" href="/staff">👤 الموظفون</a>
<a class="btn" href="/reports">📈 التقارير</a>
<a class="btn" href="/subscription">💳 الاشتراك</a>
<a class="btn" href="/api-keys">🔑 API Keys</a>
<a class="btn" href="/settings">⚙️ الإعدادات</a>
<a class="btn" href="/store/{{u["company_slug"] or "veqranto"}}">🛒 المتجر</a>
</div>

<h2 class="title">MASTER API</h2>
<div class="nav">
<a class="btn" href="/api/master/dashboard">Dashboard API</a>
<a class="btn" href="/api/master/settings">Settings API</a>
<a class="btn" href="/api/master/inventory">Inventory API</a>
<a class="btn" href="/api/master/coupons">Coupons API</a>
<a class="btn" href="/api/master/audit">Audit API</a>
<a class="btn" href="/api/master/report">Reports API</a>
</div>

<h2 class="title">حالة النظام</h2>
<div class="card">
<p>الخدمة: <b>VEQRANTO SaaS v3.0</b></p>
<p>الشركة: <b>{{u["company_name"]}}</b></p>
<p>Company ID: <b>{{u["company_id"]}}</b></p>
<p><small>هذه اللوحة تستخدم بيانات الشركة الحالية ولا تعرض بيانات الشركات الأخرى.</small></p>
</div>

</div>
</body>
</html>
""",u=u,data=data)

# Keep existing master APIs, add the unified UI.
