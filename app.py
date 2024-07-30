from flask import Flask, render_template, flash, request, session, redirect, url_for, send_from_directory
from pymongo import MongoClient, DESCENDING
import os
from bson import ObjectId
import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "varun"
client = MongoClient('mongodb://localhost:27017/')
db = client['herbalverify']
users_collection = db['users']
plantleaf_collection = db["plantleaf"]
hdisease_collection = db['hdisease']
doc_collection = db["doc"]
post_collection = db["post"]

UPLOAD_FOLDER = 'uploads'  # Folder to store uploaded images
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Function to authenticate user


def authenticate(name, password):
    return users_collection.find_one({"name": name, "password": password})

# Function to create a new user


def create_user(name, email, password):
    if users_collection.find_one({"name": name}):
        return False  # User with the same name already exists
    else:
        users_collection.insert_one(
            {"name": name, "email": email, "password": password})
        return True


@app.route("/")
def login():
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login_post():
    name, password = request.form["name"], request.form["password"]
    if authenticate(name, password):
        session["user"] = name
        return render_template("home.html")
    else:
        flash("Invalid name or password. Please try again.")
        return render_template("login.html")


@app.route("/home")
def home():
    if "user" in session:
        return render_template("home.html")
    else:
        return render_template("login.html")


@app.route("/ayurvedicShop")
def ayurvedicShop():
    return render_template("ayurvedicShop.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html")
    elif request.method == "POST":
        name, email, password = (
            request.form["name"],
            request.form["email"],
            request.form["password"],
        )
        if create_user(name, email, password):
            flash("Account created successfully! Please login.")
            return render_template("login.html")
        else:
            flash(
                "User with the same name already exists. Please choose a different name."
            )
            return render_template("signup.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/scan", methods=["GET", "POST"])
def scan():
    if request.method == "POST":
        prediction_class = request.form.get("prediction_class")
        if prediction_class:
            plant_data = plantleaf_collection.find_one(
                {"pname": prediction_class})
            return render_template("scan.html", plantData=plant_data)
    return render_template("scan.html")


@app.route("/scanDisease")
def scanDisease():
    return render_template("scanDisease.html")


@app.route("/nursery")
def nursery():
    return render_template("nursery.html")


@app.route("/homeRemedies")
def homeRemedies():
    return render_template("homeRemedies.html")

# Function to search for disease
def search_disease(query):
    results = hdisease_collection.find(
        {"dname": {"$regex": query, "$options": "i"}})
    return [result for result in results]


@app.route("/search", methods=["GET"])
def search():
    query = request.args.get("disease")
    if query:
        results = search_disease(query)
    else:
        results = []
    return render_template("homeRemedies.html", results=results)


@app.route('/uploadDoc')
def uploadDoc():
    return render_template('uploadDoc.html')


@app.route('/upload', methods=['POST'])
def upload():
    if request.method == 'POST':
        image = request.files['image']
        name = request.form['name']
        specialization = request.form['specialization']
        degree = request.form['degree']
        contact = request.form['contact']
        appointment = request.form['appointment']

        if image.filename != '':
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])

            filename = os.path.join(
                app.config['UPLOAD_FOLDER'], secure_filename(image.filename))
            image.save(filename)
            image_url = '/uploads/' + secure_filename(image.filename)
        else:
            image_url = None

        doctor_data = {
            'image': image_url,
            'name': name,
            'specialization': specialization,
            'degree': degree,
            'contact': contact,
            'time': appointment
        }
        doc_collection.insert_one(doctor_data)

        flash('Registration successful', 'success')
        return redirect(url_for('uploadDoc'))


@app.route('/doctor_data')
def doctor_data():
    doctors = doc_collection.find()
    return render_template('doctor_data.html', doctors=doctors)


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/pimpal')
def pimpal():
    return render_template('pimpal.html')


def get_approved_posts():
    return post_collection.find({'approved': True}).sort('_id', DESCENDING)


@app.route('/post')
def post():
    posts = get_approved_posts()
    return render_template('post.html', posts=posts)


@app.route('/submitPost', methods=['GET', 'POST'])
def submitPost():
    if request.method == 'POST':
        full_name = request.form['full-name']
        post_title = request.form['post-title']
        post_description = request.form['post-description']

        if 'image' in request.files:
            image = request.files['image']
            if image.filename != '':
                filename = os.path.join(
                    app.config['UPLOAD_FOLDER'], secure_filename(image.filename))
                image.save(filename)
                image_url = '/' + filename
            else:
                image_url = None
        else:
            image_url = None

        post_data = {
            'full_name': full_name,
            'post_title': post_title,
            'post_description': post_description,
            'image_url': image_url,
            'date': datetime.datetime.now(),
            'likes': 0,
            'dislikes': 0,
            'approved': False
        }
        post_collection.insert_one(post_data)
        flash('Your post request is sended', 'success')
        return redirect(url_for('submitPost'))
    return render_template('submitPost.html')


@app.route('/adminPost')
def adminPost():
    pending_posts = post_collection.find({'approved': False})
    return render_template('adminPost.html', pending_posts=pending_posts)


@app.route('/approve_post/<post_id>')
def approve_post(post_id):
    post_collection.update_one({'_id': ObjectId(post_id)}, {
                               '$set': {'approved': True}})
    return redirect(url_for('adminPost'))


@app.route('/reject_post/<post_id>')
def reject_post(post_id):
    post_collection.delete_one({'_id': ObjectId(post_id)})
    flash('Post rejected successfully!', 'danger')
    return redirect(url_for('adminPost'))


if __name__ == '__main__':
    app.run(debug=True)
