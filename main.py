from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
import smtplib
from email.mime.text import MIMEText  # تصحيح: MIMEText (بحروف كبيرة)
from email.mime.multipart import MIMEMultipart  # تصحيح: MIMEMultipart (بحروف كبيرة)
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from wtforms import StringField, SubmitField, IntegerField, SelectField
from wtforms.validators import DataRequired, URL, length
import csv
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime

# إيميلات الإرسال والاستقبال
OWN_EMAIL = "rnsdoodi9@gmail.com"
OWN_PASSWORD = "ooen nmly yifc uioc"

# إضافة بريد إضافي للاستقبال (يمكنك تغييره)
RECEIVER_EMAIL = "rnsdoodi9@gmail.com"  # البريد الذي ستستلم عليه الرسائل

all_cvs = []
all_users = []
all_temps = []

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "any secret key yes")

Bootstrap(app)

# Login Manager
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(Admin_id):
    return Admins.query.get(int(Admin_id))


# DATABASE SETUP
db = SQLAlchemy(app)

uri = os.environ.get("DATABASE_URL")

if uri:
    if uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)
else:
    uri = "sqlite:///DH.db"

app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


# CREATE TABLES
class User(db.Model):
    __tablename__ = "customers1"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, nullable=False)
    Name = db.Column(db.String(250), nullable=False)
    Contact = db.Column(db.BIGINT, nullable=False)
    Nid = db.Column(db.BIGINT, nullable=False)
    Visa = db.Column(db.BIGINT, nullable=False)
    resume = db.relationship('BioData', backref='resumes')
    resume_id = db.Column(db.Integer, db.ForeignKey('bio_data.id'))


class BioData(db.Model):
    __tablename__ = "bio_data"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    review = db.Column(db.String(250), nullable=False)
    nationality = db.Column(db.String(250), nullable=False)
    img_url = db.Column(db.String(1000), nullable=False)
    resume = db.Column(db.String(1000), nullable=False)
    selector = relationship('User', backref='bio')


class Temp(db.Model):
    __tablename__ = "temp"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    review = db.Column(db.String(250), nullable=False)
    nationality = db.Column(db.String(250), nullable=False)
    img_url = db.Column(db.String(1000), nullable=False)
    resume = db.Column(db.String(1000), nullable=False)


class Admins(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(1000))
    email = db.Column(db.String(250), unique=True)
    password = db.Column(db.String(250))


# إضافة جدول جديد لتخزين رسائل الاتصال
class ContactMessage(db.Model):
    __tablename__ = "contact_messages"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    message = db.Column(db.Text, nullable=False)
    request_type = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)


# تجنب إعادة إنشاء الجداول إذا كانت موجودة مسبقاً
with app.app_context():
    db.create_all()


# FORMS
class AddCv(FlaskForm):
    title = StringField('worker name اسم العاملة', validators=[DataRequired()],
                        render_kw={"placeholder": "الاسم الثلاثي"})
    rating = IntegerField('worker age العمر', validators=[DataRequired()])
    review = SelectField('worker position المهنة',
                         choices=["عاملة منزلية", "ممرضة منزلية", "مربية/جليسة أطفال", "طباخة", "سائق خاص",
                                  "عامل منزلي"])
    nationality = SelectField('Nationality الجنسية', choices=["Philippines", "Uganda"])
    img_url = StringField('worker image الصورة', validators=[DataRequired()])
    resume = StringField('CV السيرة الذاتية', validators=[DataRequired()])
    submit = SubmitField('Submit / إضافة')


class EditCv(FlaskForm):
    title = StringField('worker name اسم العاملة', validators=[DataRequired()])
    rating = StringField('worker age العمر', validators=[DataRequired()])
    review = StringField('worker position المهنة', validators=[DataRequired()])
    submit = SubmitField('تعديل')


class Choice(FlaskForm):
    Name = StringField('ادخل الاسم', validators=[DataRequired()])
    Contact = StringField('رقم الجوال', validators=[DataRequired(), length(max=10)])
    Nid = StringField('رقم الهوية/الإقامة', validators=[DataRequired(), length(max=10)])
    Visa = StringField('رقم التأشيرة(الصادر)', validators=[DataRequired(), length(max=10)])
    author_id = IntegerField('Worker ID الرجاء إدخال رقم تعريف العاملة المطلوبة ', validators=[DataRequired()])
    submit = SubmitField('اختيار')


# ========== دالة محسّنة لإرسال الإيميل (مصححة) ==========
def send_email(name, email, phone, message, request_type="استفسار"):
    """
    إرسال إيميل عند ملء نموذج الاتصال
    """
    try:
        # تنسيق الإيميل بشكل احترافي
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        email_body = f"""
        📧 رسالة جديدة من موقع WORKFORCE SAUDIA
        ═══════════════════════════════════════

        📅 التاريخ: {current_time}

        👤 معلومات المرسل:
        ─────────────────────────
        الاسم: {name}
        البريد الإلكتروني: {email}
        رقم الجوال: {phone}

        📋 تفاصيل الرسالة:
        ─────────────────────────
        نوع الطلب: {request_type}

        ✉️ نص الرسالة:
        {message}

        ═══════════════════════════════════════
        تم الإرسال من نموذج الاتصال في الموقع
        """

        # إرسال الإيميل باستخدام SMTP
        with smtplib.SMTP("smtp.gmail.com", 587) as connection:
            connection.starttls()
            connection.login(OWN_EMAIL, OWN_PASSWORD)

            # إرسال نسخة نصية
            connection.sendmail(
                OWN_EMAIL,
                RECEIVER_EMAIL,
                email_body.encode("UTF-8")
            )

        return True

    except Exception as e:
        print(f"⚠️ خطأ في إرسال الإيميل: {e}")
        return False


# ========== ROUTE خاص بنموذج الاتصال ==========
@app.route("/contact", methods=["GET", "POST"])
def get_data():
    """
    استقبال بيانات نموذج الاتصال وإرسالها عبر البريد الإلكتروني
    """
    if request.method == "POST":
        # جلب البيانات من النموذج
        name = request.form.get("full-name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        message = request.form.get("message", "").strip()
        request_type = request.form.get("request_type", "استفسار")

        # التحقق من صحة البيانات
        if not name or not phone or not message:
            flash("❌ الرجاء ملء جميع الحقول المطلوبة", "error")
            return redirect(url_for('home') + "#contact")

        # حفظ الرسالة في قاعدة البيانات
        try:
            new_message = ContactMessage(
                name=name,
                email=email,
                phone=phone,
                message=message,
                request_type=request_type
            )
            db.session.add(new_message)
            db.session.commit()
        except Exception as e:
            print(f"⚠️ خطأ في حفظ الرسالة: {e}")

        # إرسال الإيميل
        email_sent = send_email(name, email, phone, message, request_type)

        if email_sent:
            flash("✅ تم إرسال رسالتك بنجاح! سنتواصل معك قريباً.", "success")
        else:
            flash("⚠️ حدث خطأ في الإرسال. الرجاء المحاولة مرة أخرى أو الاتصال بنا مباشرة.", "error")

        return redirect(url_for('home') + "#contact")

    return redirect(url_for('home'))


# ========== باقي Routes الموجودة ==========
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/select")
def select():
    return render_template("cards.html")


@app.route("/philippines")
def philippines():
    all_cvs = Temp.query.all()
    return render_template("philippines.html", cvs=all_cvs, temps=all_temps)


@app.route("/kenya")
def kenya():
    all_cvs = Temp.query.all()
    return render_template("kenya.html", cvs=all_cvs, temps=all_temps)


@app.route("/add", methods=["GET", "POST"])
def add():
    form = AddCv()

    total_workers = User.query.count()
    total_temp = Temp.query.count()
    total_requests = BioData.query.count()

    if form.validate_on_submit():
        new_resume = Temp(
            title=form.title.data,
            rating=form.rating.data,
            review=form.review.data,
            nationality=form.nationality.data,
            img_url=form.img_url.data,
            resume=form.resume.data,
        )

        new_cv = BioData(
            title=form.title.data,
            rating=form.rating.data,
            review=form.review.data,
            nationality=form.nationality.data,
            img_url=form.img_url.data,
            resume=form.resume.data,
        )

        with open("cvs-data.csv", mode="a", encoding="utf8") as csv_file:
            csv_file.write(f"\n{form.title.data},"
                           f"{form.rating.data},"
                           f"{form.review.data},"
                           f"{form.nationality.data},"
                           f"{form.img_url.data},"
                           f"{form.resume.data},"
                           )

        db.session.add(new_cv)
        db.session.add(new_resume)
        db.session.commit()
        all_cvs.append(new_cv)
        all_temps.append(new_resume)
        flash("✔!! تم إضافة العاملة بنجاح ")
        return redirect(url_for('add'))

    return render_template(
        "add.html",
        form=form,
        total_workers=total_workers,
        total_temp=total_temp,
        total_requests=total_requests
    )


@app.route("/edit", methods=["GET", "POST"])
def edit():
    form = EditCv()
    cv_id = request.args.get("id")
    updated_cv = BioData.query.get(cv_id)
    if form.validate_on_submit():
        updated_cv.title = form.title.data
        updated_cv.rating = form.rating.data
        updated_cv.review = form.review.data
        db.session.commit()
        flash("✔ تم تعديل بيانات العاملة بنجاح")
        return redirect(url_for('Dh_list'))
    return render_template("edit.html", form=form, cv=updated_cv)


@app.route("/temp_edit", methods=["GET", "POST"])
def temp_edit():
    form = EditCv()
    temp_id = request.args.get("id")
    updated_temp = Temp.query.get(temp_id)
    if form.validate_on_submit():
        updated_temp.title = form.title.data
        updated_temp.rating = form.rating.data
        updated_temp.review = form.review.data
        db.session.commit()
        flash("✔ تم تعديل بيانات العاملة بنجاح")
        return redirect(url_for('temp_list'))
    return render_template("temp_edit.html", form=form, temp=updated_temp)


@app.route("/delete")
def delete():
    cv_id = request.args.get("id")
    cv_to_delete = BioData.query.get(cv_id)
    db.session.delete(cv_to_delete)
    db.session.commit()
    flash("✔ تم حذف العاملة بنجاح")
    return redirect(url_for('Dh_list'))


@app.route("/temp_delete")
def temp_delete():
    cv_id = request.args.get("id")
    cv_to_delete = Temp.query.get(cv_id)
    db.session.delete(cv_to_delete)
    db.session.commit()
    flash("✔ تم حذف العاملة بنجاح")
    return redirect(url_for('temp_list'))


@app.route("/choice/<int:cvs_id>", methods=["GET", "POST"])
def choice(cvs_id):
    form = Choice()
    cv_id = request.args.get("id")
    cv_to_select = Temp.query.get(cv_id)
    selector = cvs_id
    if form.validate_on_submit():
        new_user = User(
            Name=form.Name.data,
            Contact=form.Contact.data,
            Nid=form.Nid.data,
            Visa=form.Visa.data,
            author_id=form.author_id.data,
            resume_id=selector
        )

        if form.author_id.data == cvs_id:
            cv_to_select = db.session.query(Temp).get(cvs_id)
            db.session.delete(cv_to_select)
            db.session.commit()

            db.session.add(new_user)
            db.session.commit()
            all_users.append(new_user)
            flash(f" 0{new_user.Contact} تم الاختيار بنجاح وسوف نقوم بالتواصل معكم على الرقم ")
        else:
            flash("رقم تعريف خاطئ او ان العاملة غير متاحة حالياً, الرجاء التأكد والمحاولة مرة أخرى")

        return redirect(url_for('philippines'))
    return render_template("choice.html", form=form, users=all_users, select=cv_to_select, cvs=all_cvs, cv=cvs_id)


@app.route("/cvs")
def cvs():
    with open('cvs-data.csv', newline='', encoding="utf8") as csv_file:
        csv_data = csv.reader(csv_file, delimiter=',')
        list_of_rows = []
        for row in csv_data:
            list_of_rows.append(row)
        return render_template('cvs.html', cvs=list_of_rows)


@app.route("/list")
def Dh_list():
    added_cvs = BioData.query.all()
    return render_template("list.html", cvs=added_cvs)


@app.route("/temp_list")
def temp_list():
    added_temps = Temp.query.all()
    return render_template("temp_list.html", temps=added_temps, temp=cvs)


@app.route("/selections")
def selections():
    new_user = User.query.all()
    return render_template("selections.html", users=new_user, cvs=all_cvs)


@app.route("/reject/<int:users_id>", methods=["GET", "POST"])
def reject(users_id):
    user_to_delete = db.session.query(User).get(users_id)
    db.session.delete(user_to_delete)
    db.session.commit()
    flash(" ✔ تم حذف الطلب  ")
    return redirect(url_for('selections'))


@app.route("/policy")
def policy():
    return render_template("policy.html")


@app.route("/questions")
def questions():
    return render_template("questions.html")


@app.route("/insurance")
def insurance():
    return send_from_directory('static', filename="files/Insurance.pdf")


@app.route("/visa")
def visa():
    return send_from_directory('static', filename="files/visa.pdf")


@app.route("/salary")
def salary():
    return send_from_directory('static', filename="files/salary.pdf")


@app.route("/electronic")
def electronic():
    return send_from_directory('static', filename="files/electronic.pdf")


@app.route("/replace")
def replace():
    return send_from_directory('static', filename="files/replace.pdf")


@app.route("/evisa")
def evisa():
    return send_from_directory('static', filename="files/evisa.jpg")


@app.route("/musaned")
def musaned():
    return send_from_directory('static', filename="files/musaned.pdf")


@app.route("/cancel")
def cancel():
    return send_from_directory('static', filename="files/cancel.jpg")


# Authentication Part for (Admins)
@app.route('/admins')
def sign():
    return render_template("main.html")


@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        if Admins.query.filter_by(email=request.form.get('email')).first():
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))

        hash_and_salted_password = generate_password_hash(
            request.form.get('password'),
            method='pbkdf2:sha256',
            salt_length=8
        )
        new_admin = Admins(
            email=request.form.get('email'),
            name=request.form.get('name'),
            password=hash_and_salted_password,
        )
        db.session.add(new_admin)
        db.session.commit()
        login_user(new_admin)
        flash("تم التسجيل بنجاح, رجاءا قم بالعودة الى صفحة الدخول")
        return redirect(url_for("register"))
    return render_template("register.html", logged_in=current_user.is_authenticated)


@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')
        admin = Admins.query.filter_by(email=email).first()
        if not admin:
            flash("That email does not exist, please try again.")
            return redirect(url_for('login'))
        elif not check_password_hash(admin.password, password):
            flash('Password incorrect, please try again.', 'danger')
            return redirect(url_for('login'))
        else:
            login_user(admin)
            return redirect(url_for('admin'))
    return render_template("login.html", logged_in=current_user.is_authenticated)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('sign'))


@app.route('/admin')
@login_required
def admin():
    print(current_user.name)
    return render_template("add.html", logged_in=True, name=current_user.name)


if __name__ == "__main__":
    app.run(debug=True)