
from flask import jsonify, request, session, render_template_string
import sqlite3, hashlib, datetime, secrets

def register_master_features(app):

    ROOT_DB = __import__("pathlib").Path(__file__).resolve().parent/"veqranto.db"

    def db():
        c=sqlite3.connect(ROOT_DB)
        c.row_factory=sqlite3.Row
        return c

    def company_id():
        try:
            uid=session.get("uid")
            if not uid:
                return None
            c=db()
            r=c.execute(
                "SELECT company_id FROM users WHERE id=? AND active=1",
                (uid,)
            ).fetchone()
            c.close()
            return r["company_id"] if r else None
        except Exception:
            return None

    def api_company():
        auth=request.headers.get("Authorization","")
        if not auth.startswith("Bearer "):
            return None
        raw=auth[7:].strip()
        digest=hashlib.sha256(raw.encode()).hexdigest()
        c=db()
        r=c.execute(
            "SELECT company_id FROM api_keys WHERE key_hash=? AND active=1",
            (digest,)
        ).fetchone()
        c.close()
        return r["company_id"] if r else None

    @app.route("/api/master/dashboard")
    def master_dashboard():
        cid=company_id() or api_company()
        if not cid:
            return jsonify(ok=False,error="unauthorized"),401

        c=db()

        def count(table):
            try:
                return c.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE company_id=?",
                    (cid,)
                ).fetchone()[0]
            except Exception:
                return 0

        products=count("products")
        customers=count("customers")
        orders=count("orders")
        expenses=count("expenses")

        sales=0
        try:
            sales=c.execute(
                "SELECT COALESCE(SUM(total),0) FROM orders "
                "WHERE company_id=?",
                (cid,)
            ).fetchone()[0]
        except Exception:
            pass

        low_stock=0
        try:
            low_stock=c.execute(
                "SELECT COUNT(*) FROM products "
                "WHERE company_id=? AND active=1 "
                "AND stock<=min_stock",
                (cid,)
            ).fetchone()[0]
        except Exception:
            pass

        c.close()

        return jsonify(
            ok=True,
            company_id=cid,
            statistics={
                "products":products,
                "customers":customers,
                "orders":orders,
                "expenses":expenses,
                "sales":sales,
                "low_stock":low_stock
            }
        )

    @app.route("/api/master/settings",methods=["GET","POST"])
    def master_settings():
        cid=company_id() or api_company()
        if not cid:
            return jsonify(ok=False,error="unauthorized"),401

        c=db()

        if request.method=="POST":
            data=request.get_json(silent=True) or request.form.to_dict()

            for k,v in data.items():
                if k in {
                    "currency","currency_symbol","country",
                    "language","timezone","payment_default",
                    "store_enabled","inventory_enabled",
                    "coupons_enabled","notifications_enabled",
                    "low_stock_enabled"
                }:
                    c.execute("""
                    INSERT INTO company_settings
                    (company_id,setting_key,setting_value)
                    VALUES(?,?,?)
                    ON CONFLICT(company_id,setting_key)
                    DO UPDATE SET setting_value=excluded.setting_value
                    """,(cid,k,str(v)))

            c.commit()

        rows=c.execute(
            "SELECT setting_key,setting_value "
            "FROM company_settings WHERE company_id=?",
            (cid,)
        ).fetchall()

        c.close()

        return jsonify(
            ok=True,
            settings={r["setting_key"]:r["setting_value"] for r in rows}
        )

    @app.route("/api/master/inventory",methods=["GET","POST"])
    def master_inventory():
        cid=company_id() or api_company()
        if not cid:
            return jsonify(ok=False,error="unauthorized"),401

        c=db()

        if request.method=="POST":
            data=request.get_json(silent=True) or {}
            pid=data.get("product_id")
            qty=float(data.get("quantity",0))
            movement=data.get("movement_type","adjustment")
            note=data.get("note","")

            if not pid or qty==0:
                c.close()
                return jsonify(ok=False,error="product_id and quantity required"),400

            p=c.execute(
                "SELECT stock FROM products "
                "WHERE id=? AND company_id=?",
                (pid,cid)
            ).fetchone()

            if not p:
                c.close()
                return jsonify(ok=False,error="product not found"),404

            new_stock=float(p["stock"] or 0)+qty

            c.execute(
                "UPDATE products SET stock=? "
                "WHERE id=? AND company_id=?",
                (new_stock,pid,cid)
            )

            c.execute("""
            INSERT INTO inventory_movements
            (company_id,product_id,user_id,quantity,movement_type,note)
            VALUES(?,?,?,?,?,?)
            """,(cid,pid,session.get("uid"),qty,movement,note))

            c.commit()

        rows=c.execute("""
        SELECT p.id,p.name,p.sku,p.stock,p.min_stock,
        CASE WHEN p.stock<=p.min_stock THEN 1 ELSE 0 END low_stock
        FROM products p
        WHERE p.company_id=? AND p.active=1
        ORDER BY low_stock DESC,p.id DESC
        """,(cid,)).fetchall()

        c.close()

        return jsonify(
            ok=True,
            products=[dict(r) for r in rows]
        )

    @app.route("/api/master/coupons",methods=["GET","POST","DELETE"])
    def master_coupons():
        cid=company_id() or api_company()
        if not cid:
            return jsonify(ok=False,error="unauthorized"),401

        c=db()

        if request.method=="POST":
            d=request.get_json(silent=True) or {}
            code=str(d.get("code","")).strip().upper()

            if not code:
                c.close()
                return jsonify(ok=False,error="code required"),400

            try:
                c.execute("""
                INSERT INTO coupons
                (company_id,code,discount_type,discount_value,
                 min_order,max_uses,expires_at,active)
                VALUES(?,?,?,?,?,?,?,1)
                """,(
                    cid,code,
                    d.get("discount_type","percent"),
                    float(d.get("discount_value",0)),
                    float(d.get("min_order",0)),
                    int(d.get("max_uses",0)),
                    d.get("expires_at")
                ))
                c.commit()
            except sqlite3.IntegrityError:
                c.close()
                return jsonify(ok=False,error="coupon already exists"),409

        if request.method=="DELETE":
            cid2=request.args.get("id")
            c.execute(
                "UPDATE coupons SET active=0 "
                "WHERE id=? AND company_id=?",
                (cid2,cid)
            )
            c.commit()

        rows=c.execute("""
        SELECT id,code,discount_type,discount_value,
        min_order,max_uses,used_count,active,expires_at,created_at
        FROM coupons
        WHERE company_id=?
        ORDER BY id DESC
        """,(cid,)).fetchall()

        c.close()

        return jsonify(ok=True,coupons=[dict(r) for r in rows])

    @app.route("/api/master/audit")
    def master_audit():
        cid=company_id() or api_company()
        if not cid:
            return jsonify(ok=False,error="unauthorized"),401

        c=db()
        rows=c.execute("""
        SELECT id,user_id,action,entity_type,
        entity_id,details,created_at
        FROM audit_logs
        WHERE company_id=?
        ORDER BY id DESC LIMIT 200
        """,(cid,)).fetchall()
        c.close()

        return jsonify(ok=True,logs=[dict(r) for r in rows])

    @app.route("/api/master/report")
    def master_report():
        cid=company_id() or api_company()
        if not cid:
            return jsonify(ok=False,error="unauthorized"),401

        c=db()

        sales=c.execute("""
        SELECT COALESCE(SUM(total),0)
        FROM orders WHERE company_id=?
        """,(cid,)).fetchone()[0]

        orders=c.execute("""
        SELECT COUNT(*) FROM orders WHERE company_id=?
        """,(cid,)).fetchone()[0]

        expenses=c.execute("""
        SELECT COALESCE(SUM(amount),0)
        FROM expenses WHERE company_id=?
        """,(cid,)).fetchone()[0]

        customers=c.execute("""
        SELECT COUNT(*) FROM customers WHERE company_id=?
        """,(cid,)).fetchone()[0]

        products=c.execute("""
        SELECT COUNT(*) FROM products
        WHERE company_id=? AND active=1
        """,(cid,)).fetchone()[0]

        c.close()

        return jsonify(
            ok=True,
            report={
                "sales":sales,
                "orders":orders,
                "expenses":expenses,
                "customers":customers,
                "products":products,
                "net":float(sales or 0)-float(expenses or 0)
            }
        )

    @app.route("/master")
    def master_center():
        if not session.get("uid"):
            return __import__("flask").redirect("/login")

        return render_template_string("""
<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>VEQRANTO Control Center</title>
<style>
body{margin:0;background:#0b1020;color:#eef2ff;font-family:Arial,sans-serif}
.wrap{max-width:1200px;margin:auto;padding:24px}
h1{margin-bottom:6px}
.sub{opacity:.65;margin-bottom:25px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px}
.card{background:#151c31;border:1px solid #27304a;border-radius:16px;padding:20px}
.num{font-size:28px;font-weight:bold;margin-top:10px}
.panel{margin-top:20px;background:#151c31;border-radius:16px;padding:20px}
button{border:0;border-radius:10px;padding:12px 18px;cursor:pointer}
pre{white-space:pre-wrap;word-break:break-word}
</style>
</head>
<body>
<div class="wrap">
<h1>VEQRANTO</h1>
<div class="sub">Master Control Center</div>
<div id="cards" class="grid"></div>
<div class="panel">
<h2>System Report</h2>
<pre id="report">Loading...</pre>
</div>
</div>
<script>
async function load(){
 let r=await fetch('/api/master/dashboard');
 let d=await r.json();
 if(!d.ok){location='/login';return}
 let s=d.statistics;
 let cards=[
 ['المنتجات',s.products],
 ['العملاء',s.customers],
 ['الطلبات',s.orders],
 ['المصروفات',s.expenses],
 ['المبيعات',s.sales],
 ['مخزون منخفض',s.low_stock]
 ];
 document.getElementById('cards').innerHTML=
 cards.map(x=>`<div class="card"><div>${x[0]}</div><div class="num">${x[1]}</div></div>`).join('');

 let rr=await fetch('/api/master/report');
 document.getElementById('report').textContent=
 JSON.stringify(await rr.json(),null,2);
}
load();
</script>
</div>
</body>
</html>
""")

    return True
