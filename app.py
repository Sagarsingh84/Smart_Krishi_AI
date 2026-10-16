import os,csv,math,uuid,hmac
from pathlib import Path
from datetime import datetime,timezone
from functools import wraps
from flask import Flask,render_template,request,jsonify,session,redirect,url_for,flash
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash,check_password_hash
load_dotenv()
app=Flask(__name__)
app.secret_key=os.getenv("FLASK_SECRET_KEY","change-this-secret-before-deployment")
BASE=Path(__file__).resolve().parent
with open(BASE/"data"/"crop_data.csv",newline="",encoding="utf-8") as f: CROPS=list(csv.DictReader(f))
db = None
client = None
mongo_status = "Demo mode: MongoDB Atlas not connected."

try:
    uri = os.getenv("MONGODB_URI", "").strip()

    if not uri:
        raise ValueError("MONGODB_URI is missing from .env")

    from pymongo import MongoClient

    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")  # Verify the connection

    db_name = os.getenv("MONGODB_DB", "smart_krishi").strip()
    db = client[db_name]

    mongo_status = f"Connected to MongoDB Atlas: {db_name}"

except Exception as e:
    db = None
    mongo_status = f"MongoDB connection failed: {e}"
    print(mongo_status)

demo_users={};demo_profiles={};demo_predictions=[]
def admin_required(fn):
 @wraps(fn)
 def wrap(*a,**kw):
  if not session.get("is_admin"): return redirect(url_for("admin_login"))
  return fn(*a,**kw)
 return wrap
def login_required(fn):
 @wraps(fn)
 def wrap(*a,**kw):
  if not session.get("uid"): return redirect(url_for("login")) if not request.path.startswith("/api/") else (jsonify(ok=False,error="Please log in first."),401)
  return fn(*a,**kw)
 return wrap
def get_user():
 uid=session.get("uid")
 if not uid:return None
 try:
  u=db.users.find_one({"_id":uid},{"password_hash":0}) if db is not None else demo_users.get(uid)
  if u and "password_hash" in u:u={k:v for k,v in u.items() if k!="password_hash"}
  return u
 except Exception:return None
def val(d,k,label,lo,hi):
 try:v=float(d.get(k,""))
 except:v=float("nan")
 if not math.isfinite(v) or v<lo or v>hi:raise ValueError(f"Enter a valid {label} between {lo} and {hi}.")
 return v
def clamp(v):return max(0,min(100,v))
def score(v,lo,hi,tol):
 return 100 if lo<=v<=hi else clamp(100-(lo-v if v<lo else v-hi)/tol*100)
def predict(d,uid):
 state=d.get("state","").strip();district=d.get("district","").strip();season=d.get("season","");soil=d.get("soil_type","");water=d.get("irrigation","")
 if not state or not district:raise ValueError("Enter state and district.")
 if season not in ["Kharif","Rabi","Zaid","Year-round"]:raise ValueError("Choose a valid season.")
 n=val(d,"nitrogen","nitrogen",0,300);p=val(d,"phosphorus","phosphorus",0,200);k=val(d,"potassium","potassium",0,300);ph=val(d,"ph","soil pH",0,14);rain=val(d,"rainfall","rainfall",0,3000);acres=val(d,"acres","farm size",.01,100000)
 out=[]
 for c in CROPS:
  if season!="Year-round" and c["season"] not in (season,"Year-round"):continue
  soils=c["soil_types"].split(";")
  bonus=8 if soil in soils else 0
  wb=7 if water=="Rainfed" and c["water_need"]=="Low" else (-8 if water=="Rainfed" and c["water_need"]=="High" else (5 if water=="Limited" and c["water_need"]=="Low" else (8 if water=="Reliable" and c["water_need"]=="High" else 2)))
  s=clamp(.22*score(n,float(c["n_min"]),float(c["n_max"]),70)+.16*score(p,float(c["p_min"]),float(c["p_max"]),50)+.16*score(k,float(c["k_min"]),float(c["k_max"]),70)+.22*score(ph,float(c["ph_min"]),float(c["ph_max"]),2.5)+.18*score(rain,float(c["rain_min"]),float(c["rain_max"]),700)+bonus+wb)
  y=float(c["yield_tonnes_per_acre"])*(.55+.45*s/100);price=float(c["price_inr_per_tonne"]);cost=float(c["cost_inr_per_acre"]);rev=y*price;profit=rev-cost
  out.append(dict(crop=c["crop"],season=c["season"],suitability=round(s,1),yield_per_acre=round(y,2),revenue_per_acre=round(rev),cost_per_acre=round(cost),profit_per_acre=round(profit),total_profit=round(profit*acres),water_need=c["water_need"],notes=c["notes"]))
 out=sorted([x for x in out if x["suitability"]>=25],key=lambda x:(x["profit_per_acre"],x["suitability"]),reverse=True)[:3]
 if not out:raise ValueError("No suitable demo crops found. Try another season or check inputs.")
 return dict(created_at=datetime.now(timezone.utc).isoformat(),farmer_id=uid,state=state,district=district,season=season,soil_type=soil,irrigation=water,soil=dict(nitrogen=n,phosphorus=p,potassium=k,ph=ph,rainfall_mm=rain),acres=acres,top_crops=out,data_mode="demo_estimates")
@app.route("/")
@login_required
def dashboard():
    user = get_user()

    # Handle missing or expired farmer sessions
    if user is None:
        session.pop("uid", None)
        flash("Please log in again to continue.", "error")
        return redirect(url_for("login"))

    return render_template(
        "dashboard.html",
        user=user,
        mongo_status=mongo_status
    )

@app.route("/register",methods=["GET","POST"])
def register():
 if request.method=="POST":
  name=request.form.get("name","").strip();email=request.form.get("email","").strip().lower();pw=request.form.get("password","")
  if len(name)<2 or "@" not in email or len(pw)<8:flash("Enter a name, valid email, and password of at least 8 characters.","error")
  else:
   try:
    exists=db.users.find_one({"email":email}) if db is not None else any(u["email"]==email for u in demo_users.values())
    if exists:flash("This email is already registered.","error")
    else:
     uid=uuid.uuid4().hex;user={"_id":uid,"name":name,"email":email,"password_hash":generate_password_hash(pw),"created_at":datetime.now(timezone.utc).isoformat()}
     if db is not None:db.users.insert_one(user)
     else:demo_users[uid]=user
     session["uid"]=uid;return redirect(url_for("profile"))
   except Exception:flash("Registration failed. Check your Atlas connection.","error")
 return render_template("register.html")
@app.route("/login",methods=["GET","POST"])
def login():
 if request.method=="POST":
  email=request.form.get("email","").strip().lower();pw=request.form.get("password","")
  try:u=db.users.find_one({"email":email}) if db is not None else next((x for x in demo_users.values() if x["email"]==email),None)
  except Exception:u=None
  if u and check_password_hash(u.get("password_hash",""),pw):session["uid"]=u["_id"];return redirect(url_for("dashboard"))
  flash("Invalid email or password. Demo accounts disappear when server stops.","error")
 return render_template("login.html")
@app.route("/logout",methods=["POST"])
def logout():session.clear();return redirect(url_for("login"))
@app.route("/profile",methods=["GET","POST"])
@login_required
def profile():
 uid=session["uid"]
 if request.method=="POST":
  d=dict(farmer_id=uid,phone=request.form.get("phone","").strip(),state=request.form.get("state","").strip(),district=request.form.get("district","").strip(),village=request.form.get("village","").strip(),farm_size_acres=request.form.get("farm_size_acres","").strip(),soil_type=request.form.get("soil_type",""),irrigation=request.form.get("irrigation",""),updated_at=datetime.now(timezone.utc).isoformat())
  try:
   if db is not None:db.farmer_profiles.update_one({"farmer_id":uid},{"$set":d},upsert=True)
   else:demo_profiles[uid]=d
   flash("Farmer profile saved.","success")
  except Exception:flash("Could not save profile to cloud.","error")
 try:pr=db.farmer_profiles.find_one({"farmer_id":uid},{"_id":0}) if db is not None else demo_profiles.get(uid,{})
 except Exception:pr={}
 return render_template("profile.html",user=get_user(),profile=pr or {},mongo_status=mongo_status)
@app.route("/api/predict",methods=["POST"])
@login_required
def api_predict():
 try:
  rec=predict(request.get_json(silent=True) or request.form.to_dict(),session["uid"]);saved=False
  try:
   if db is not None:db.prediction_history.insert_one(rec.copy());saved=True
   else:demo_predictions.insert(0,rec);del demo_predictions[100:]
  except Exception:pass
  return jsonify(ok=True,record=rec,saved_to_cloud=saved,message="Illustrative demo estimates, not live market data.")
 except ValueError as e:return jsonify(ok=False,error=str(e)),400
@app.route("/history")
@login_required
def history():
 uid=session["uid"]
 try:rows=list(db.prediction_history.find({"farmer_id":uid},{"_id":0}).sort("created_at",-1).limit(50)) if db is not None else [x for x in demo_predictions if x["farmer_id"]==uid][:50]
 except Exception:rows=[]
 return render_template("history.html",user=get_user(),rows=rows,mongo_status=mongo_status)

@app.route("/admin/login",methods=["GET","POST"])
def admin_login():
 if request.method=="POST":
  email=request.form.get("email","").strip().lower()
  password=request.form.get("password","")
  expected_email=os.getenv("ADMIN_EMAIL","").strip().lower()
  expected_password=os.getenv("ADMIN_PASSWORD","")
  if expected_email and expected_password and hmac.compare_digest(email,expected_email) and hmac.compare_digest(password,expected_password):
   session["is_admin"]=True
   return redirect(url_for("admin_dashboard"))
  flash("Invalid admin credentials. Configure ADMIN_EMAIL and ADMIN_PASSWORD in your .env file.","error")
 return render_template("admin_login.html")

@app.route("/admin/logout", methods=["POST"])
@admin_required
def admin_logout():
    session.pop("is_admin", None)
    session.pop("admin_email", None)
    flash("Administrator logged out.", "success")
    return redirect(url_for("admin_login"))


@app.route("/admin")
@admin_required
def admin_dashboard():
    users = []
    profiles = []
    predictions = []

    user_count = 0
    profile_count = 0
    prediction_count = 0

    try:
        if db is not None:
            users = list(
                db.users.find({}, {"password_hash": 0})
                .sort("created_at", -1)
                .limit(100)
            )

            profiles = list(
                db.farmer_profiles.find({}, {"_id": 0})
                .limit(100)
            )

            predictions = list(
                db.prediction_history.find({}, {"_id": 0})
                .sort("created_at", -1)
                .limit(20)
            )

            user_count = db.users.count_documents({})
            profile_count = db.farmer_profiles.count_documents({})
            prediction_count = db.prediction_history.count_documents({})

        else:
            users = [
                {k: v for k, v in u.items() if k != "password_hash"}
                for u in demo_users.values()
            ]
            profiles = list(demo_profiles.values())
            predictions = list(demo_predictions[:20])

            users.sort(
                key=lambda u: str(u.get("created_at", "")),
                reverse=True
            )
            predictions.sort(
                key=lambda r: str(r.get("created_at", "")),
                reverse=True
            )

            user_count = len(demo_users)
            profile_count = len(demo_profiles)
            prediction_count = len(demo_predictions)

        # Attach a profile to every user to prevent template errors.
        profiles_by_id = {
            p.get("farmer_id"): p
            for p in profiles
            if p.get("farmer_id")
        }

        for user in users:
            user["profile"] = profiles_by_id.get(
                user.get("_id"), {}
            )

        # Match prediction records to farmer email addresses.
        email_by_id = {
            user.get("_id"): user.get("email", "")
            for user in users
        }

        for record in predictions:
            record["farmer_email"] = email_by_id.get(
                record.get("farmer_id"),
                "Farmer account"
            )

    except Exception:
        app.logger.exception("Admin dashboard failed")
        flash(
            "Could not load admin records. Check the terminal.",
            "error"
        )

    return render_template(
        "admin.html",
        users=users,
        profiles=profiles,
        predictions=predictions,
        user_count=user_count,
        profile_count=profile_count,
        prediction_count=prediction_count,
        mongo_status=mongo_status
    )
    
@app.route("/api/health")
def health():return jsonify(ok=True,database=mongo_status,cloud_enabled=db is not None)
if __name__=="__main__":app.run(debug=os.getenv("FLASK_DEBUG","false").lower()=="true")


