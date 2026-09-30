from flask import Flask, render_template, request, redirect, session
from db import Base, engine, SessionLocal
import models
import fitz
import docx
import json
from ai import analyze_resume

app = Flask(__name__)
app.secret_key = "secret123"

Base.metadata.create_all(bind=engine)

#HOME
@app.route("/")
def home():
    if "user" in session:
        return redirect("/dashboard")
    return redirect("/login")

#------------SIGNUP
@app.route("/signup", methods=["GET", "POST"])
def signup():
    db = SessionLocal()

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        existing_user = db.query(models.User).filter_by(email=email).first()
        if existing_user:
            return "User already exists"

        user = models.User(email=email, password=password)
        db.add(user)
        db.commit()
        return redirect("/login")
    return render_template("signup.html")

#LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():
    db = SessionLocal()
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = db.query(models.User).filter_by(email=email, password=password).first()
        if user:
            session["user"] = user.email
            return redirect("/dashboard")
        else:
            return "Invalid Credentials"
    return render_template("login.html")

#DASHBOARD
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user" not in session:
        return redirect("/login")
    db = SessionLocal()
    user = db.query(models.User).filter_by(email=session["user"]).first()
    db.close()
    if not user:
        session.pop("user", None)
        return redirect("/login")
    result = None

    if request.method == "POST":
        user_goal = request.form.get("role")
        resume_text = request.form.get("resume")
        file = request.files.get("file")

        #file handling
        if file and file.filename != "":
            if file.filename.endswith(".pdf"):
                try:
                    pdf = fitz.open(stream=file.read(), filetype="pdf")
                    text = ""
                    for page in pdf:
                        text += page.get_text()
                        print("PDF pages:", len(pdf), "| chars extracted:" , len(text))
                    if not text.strip():
                        result = {"error": "Could not extract text from this PDF. It may be a scanned or image-based file. Please paste your resume text or upload a DOCX file."}
                    resume_text = text 
                except Exception as e:
                    result = {"error": f"PDF error: {str(e)}"}
            elif file.filename.endswith(".docx"):
                try:
                    doc = docx.Document(file)
                    text = ""
                    for para in doc.paragraphs:
                        text += para.text +"\n"
                    resume_text = text
                except Exception as e:
                    result = {"error": f"Docx error: {str(e)}"}
        # print("DEBUG >>", "goal:", user_goal, "| resume_text length:", len(resume_text or ""), "| file:", file.filename if file else None)

        if resume_text and user_goal:
            try:
                result = analyze_resume(resume_text, user_goal)
                #save to db
                db = SessionLocal()
                user = db.query(models.User).filter_by(email=session["user"]).first()
                report = models.Reports(
                    user_id =user.id,
                    resume_text = resume_text,
                    result = json.dumps(result)
                )
                db.add(report)
                db.commit()
                db.close()
            except Exception as e:
                result = {"error": f"AI error: {str(e)}"}
        elif not result:
            result = {"error": "Resume text or career goal is missing. Please paste your resume or upload a PDF/DOCX file, and enter the role you want."}

    return render_template(
        "dashboard.html",
        user= session["user"],
        result = result
    )

#histry
@app.route("/history")
def history():
    if "user" not in session:
        return redirect("/login")

    db = SessionLocal()
    user = db.query(models.User).filter_by(email=session["user"]).first()
    if not user:
        session.pop("user", None)
        return redirect("/login")
    reports = (db.query(models.Reports).filter_by(user_id = user.id).order_by(models.Reports.id.desc()).all())

    parsed_reports = []
    for i in reports:
        try:
            parsed_result = json.loads(i.result)
        except Exception:
            parsed_result = {}
        parsed_reports.append({
            "id":i.id,
            "resume":i.resume_text,
            "result":parsed_result,
        })
    db.close()
    return render_template("history.html", reports=parsed_reports)

#delete report
@app.route("/history/delete/<int:report_id>", methods=["POST"])
def delete_report(report_id):
    if "user" not in session:
        return redirect("/login")

    db = SessionLocal()
    user = db.query(models.User).filter_by(email=session["user"]).first()
    report = db.query(models.Reports).filter_by(id=report_id, user_id=user.id).first()
    if report:
        db.delete(report)
        db.commit()
    db.close()
    return redirect("/history")

#logout route
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True)

