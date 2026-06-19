import os
from datetime import datetime
from flask import Flask, flash, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "pelz"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blogs.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ── upload config ──
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ── extensions ──
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'


# ── helper ──
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ── models ──
class Blogs(db.Model):
    _id = db.Column(db.Integer(), primary_key=True)
    title = db.Column(db.String(100), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=False)
    image = db.Column(db.String(200), nullable=True)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __init__(self, title, content, user_id, image=None):
        self.title = title
        self.content = content
        self.image = image
        self.user_id = user_id


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    blogs = db.relationship('Blogs', backref='author', lazy=True)

    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.password = password


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ── DASHBOARD — public, shows ALL blogs ──────────────────────────────────────
@app.route('/')
def dashboard():
    all_blogs = Blogs.query.order_by(Blogs.date_posted.desc()).all()
    return render_template('dashboard.html', blogs=all_blogs, total=len(all_blogs))


# HOME — only shows the current user's blogs
@app.route('/home')
@login_required
def blogs():
    user_blogs = Blogs.query.filter_by(user_id=current_user.id).all()
    return render_template('home.html', blogs=user_blogs, title='Blogs Page', total=len(user_blogs))


# LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('blogs'))

    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password'].strip()
        remember = bool(request.form.get('remember'))

        user = User.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user, remember=remember)
            flash('Logged in successfully', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('blogs'))
        else:
            flash('Invalid email or password', 'danger')

    return render_template('login.html')


# LOGOUT
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))


# REGISTER
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('blogs'))

    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password']
        confirm  = request.form['confirm']

        if not username or not email or not password:
            flash('All fields are required', 'danger')
        elif password != confirm:
            flash('Passwords do not match', 'danger')
        elif len(password) < 6:
            flash('Password must be at least 6 characters', 'danger')
        elif User.query.filter_by(username=username).first():
            flash('Username already taken', 'danger')
        elif User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
        else:
            hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
            user = User(username=username, email=email, password=hashed_pw)
            db.session.add(user)
            db.session.commit()
            flash('Account created! You can now log in.', 'success')
            return redirect(url_for('login'))

    return render_template('register.html')


# ADD BLOG
@app.route('/addblog', methods=['GET', 'POST'])
@login_required
def add_blog():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        file = request.files.get('image')

        if not title or not content:
            flash('Title and content are required', 'danger')
            return render_template('addblog.html')

        if Blogs.query.filter_by(title=title).first():
            flash('A blog with this title already exists', 'danger')
            return render_template('addblog.html')

        image_filename = None
        if file and file.filename != '' and allowed_file(file.filename):
            image_filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

        blog = Blogs(title=title, content=content, user_id=current_user.id, image=image_filename)
        db.session.add(blog)

        try:
            db.session.commit()
            flash('Blog added successfully', 'success')
            return redirect(url_for('blogs'))
        except Exception as e:
            db.session.rollback()
            print(f"Error adding blog: {e}")
            flash('Something went wrong. Please try again.', 'danger')

    return render_template('addblog.html')


# VIEW BLOG
@app.route('/viewblog/<title>')
def viewblog(title):
    blog = Blogs.query.filter_by(title=title).first_or_404()
    return render_template('view_blog.html', blog=blog)


# DELETE BLOG
@app.route('/delete/<int:id>')
@login_required
def deleteuser(id):
    blog = Blogs.query.get_or_404(id)

    if blog.user_id != current_user.id:
        flash('You are not authorised to delete this blog', 'danger')
        return redirect(url_for('blogs'))

    db.session.delete(blog)
    try:
        db.session.commit()
        flash('Blog deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting blog: {e}")
        flash('Something went wrong. Please try again.', 'danger')
    return redirect(url_for('blogs'))


# UPDATE BLOG
@app.route('/updateblog/<int:id>', methods=['GET', 'POST'])
@login_required
def updateblog(id):
    blog = Blogs.query.get_or_404(id)

    if blog.user_id != current_user.id:
        flash('You are not authorised to edit this blog', 'danger')
        return redirect(url_for('blogs'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        file = request.files.get('image')

        if not title or not content:
            error = "Title and content cannot be empty."
            return render_template('updateblog.html', blog=blog, error=error)

        existing = Blogs.query.filter_by(title=title).first()
        if existing and existing._id != blog._id:
            error = "A blog with this title already exists."
            return render_template('updateblog.html', blog=blog, error=error)

        blog.title = title
        blog.content = content

        if file and file.filename != '' and allowed_file(file.filename):
            image_filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
            blog.image = image_filename

        try:
            db.session.commit()
            flash('Blog updated successfully', 'success')
            return redirect(url_for('viewblog', title=blog.title))
        except Exception as e:
            db.session.rollback()
            print(f"Error updating blog: {e}")
            error = "Something went wrong. Please try again."
            return render_template('updateblog.html', blog=blog, error=error)

    return render_template('updateblog.html', blog=blog)


# ── init db ──
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)