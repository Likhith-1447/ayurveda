from flask import Flask, request, render_template, redirect, url_for, session,jsonify
import os
import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator, load_img, img_to_array
import numpy as np
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'Ayur123' 

# Paths
train_data_dir = 'IMG_CLASSES'
upload_folder = 'uploads'
model_path = 'trained_model.h5'
os.makedirs(upload_folder, exist_ok=True)

# Image size and batch size
img_height, img_width = 224, 224
batch_size = 32

# Prepare the image data generator for training
datagen = ImageDataGenerator(rescale=1./255, validation_split=0.2)

train_generator = datagen.flow_from_directory(
    train_data_dir,
    target_size=(img_height, img_width),
    batch_size=batch_size,
    class_mode='categorical',
    subset='training'
)

validation_generator = datagen.flow_from_directory(
    train_data_dir,
    target_size=(img_height, img_width),
    batch_size=batch_size,
    class_mode='categorical',
    subset='validation'
)

# Extract class names
class_names = list(train_generator.class_indices.keys())

# Load the pre-trained model
model = tf.keras.models.load_model(model_path)

def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            author TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            body TEXT NOT NULL,
            author TEXT NOT NULL,
            question_id INTEGER,
            FOREIGN KEY (question_id) REFERENCES questions (id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS question_tags (
            question_id INTEGER,
            tag_id INTEGER,
            FOREIGN KEY (question_id) REFERENCES questions (id),
            FOREIGN KEY (tag_id) REFERENCES tags (id),
            PRIMARY KEY (question_id, tag_id)
        )
    ''')
    conn.commit()
    conn.close()


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/products')
def products():
    return render_template('products.html')

@app.route('/remedies')
def remedies():
    return render_template('remedies.html')

@app.route('/qa', methods=['GET', 'POST'])
def qa():
    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        tags = request.form.getlist('tags')
        
        if 'user' in session:
            author = session['user']
            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()
            cursor.execute('INSERT INTO questions (title, body, author) VALUES (?, ?, ?)', (title, body, author))
            question_id = cursor.lastrowid
            
            for tag in tags:
                cursor.execute('SELECT id FROM tags WHERE name = ?', (tag,))
                tag_id = cursor.fetchone()
                if not tag_id:
                    cursor.execute('INSERT INTO tags (name) VALUES (?)', (tag,))
                    tag_id = cursor.lastrowid
                else:
                    tag_id = tag_id[0]
                cursor.execute('INSERT INTO question_tags (question_id, tag_id) VALUES (?, ?)', (question_id, tag_id))
            
            conn.commit()
            conn.close()
            return redirect(url_for('qa'))
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM questions')
    questions = cursor.fetchall()
    
    questions_with_answers_and_tags = []
    for question in questions:
        cursor.execute('SELECT * FROM answers WHERE question_id = ?', (question[0],))
        answers = cursor.fetchall()
        cursor.execute('''
            SELECT tags.name FROM tags
            JOIN question_tags ON tags.id = question_tags.tag_id
            WHERE question_tags.question_id = ?
        ''', (question[0],))
        tags = [tag[0] for tag in cursor.fetchall()]
        questions_with_answers_and_tags.append({
            'id': question[0],
            'title': question[1],
            'body': question[2],
            'author': question[3],
            'tags': tags,
            'answers': [{'id': answer[0], 'body': answer[1], 'author': answer[2]} for answer in answers]
        })
    
    conn.close()
    return render_template('qa.html', questions=questions_with_answers_and_tags)


@app.route('/qa/answer/<int:question_id>', methods=['POST'])
def answer(question_id):
    body = request.form['body']
    if 'user' in session:
        author = session['user']
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO answers (body, author, question_id) VALUES (?, ?, ?)', (body, author, question_id))
        conn.commit()
        conn.close()
    return redirect(url_for('qa'))

@app.route('/index1')
def contact():
    return render_template('index1.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.json['email']
        password = request.json['password']
        
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user[3], password):
            session['user'] = user[1]  # Store user name in session
            return jsonify({'message': 'Login successful', 'user': user[1]})
        else:
            return jsonify({'message': 'Invalid credentials'}), 401
    
    return render_template('login.html')

@app.route('/qa/delete_question/<int:question_id>', methods=['POST'])
def delete_question(question_id):
    if 'user' in session:
        user = session['user']
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT author FROM questions WHERE id = ?', (question_id,))
        question = cursor.fetchone()
        if question and question[0] == user:
            cursor.execute('DELETE FROM questions WHERE id = ?', (question_id,))
            cursor.execute('DELETE FROM answers WHERE question_id = ?', (question_id,))
            conn.commit()
        conn.close()
    return redirect(url_for('qa'))

@app.route('/qa/delete_answer/<int:answer_id>', methods=['POST'])
def delete_answer(answer_id):
    if 'user' in session:
        user = session['user']
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT author FROM answers WHERE id = ?', (answer_id,))
        answer = cursor.fetchone()
        if answer and answer[0] == user:
            cursor.execute('DELETE FROM answers WHERE id = ?', (answer_id,))
            conn.commit()
        conn.close()
    return redirect(url_for('qa'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        data = request.json
        name = data['name']
        email = data['email']
        password = generate_password_hash(data['password'])
        
        try:
            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (name, email, password) VALUES (?, ?, ?)', (name, email, password))
            conn.commit()
            conn.close()
            
            session['user'] = name  # Store user name in session
            return jsonify({'message': 'Signup successful', 'user': name})
        except sqlite3.IntegrityError:
            return jsonify({'message': 'Email already exists'}), 400
    
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('user', None)  # Remove user from session
    return redirect(url_for('home'))

@app.route('/profile')
def profile():
    if 'user' in session:
        user = session['user']
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()

        # Fetch user questions
        cursor.execute('SELECT id, title, body FROM questions WHERE author = ?', (user,))
        user_questions = cursor.fetchall()
        user_questions = [{'id': q[0], 'title': q[1], 'body': q[2], 'tags': []} for q in user_questions]

        # Fetch tags for each question
        for question in user_questions:
            cursor.execute('''
                SELECT tags.name FROM tags
                JOIN question_tags ON tags.id = question_tags.tag_id
                WHERE question_tags.question_id = ?
            ''', (question['id'],))
            question['tags'] = [tag[0] for tag in cursor.fetchall()]

        # Fetch user answers
        cursor.execute('SELECT body, question_id FROM answers WHERE author = ?', (user,))
        user_answers = cursor.fetchall()
        user_answers = [{'body': a[0], 'question_id': a[1], 'question_title': ''} for a in user_answers]

        # Fetch question titles for each answer
        for answer in user_answers:
            cursor.execute('SELECT title FROM questions WHERE id = ?', (answer['question_id'],))
            answer['question_title'] = cursor.fetchone()[0]

        # Fetch cart items
        cursor.execute('SELECT id FROM users WHERE name = ?', (user,))
        user_id = cursor.fetchone()[0]
        cursor.execute('SELECT product_name, price FROM cart_items WHERE user_id = ?', (user_id,))
        cart_items = cursor.fetchall()
        cart_items = [{'product_name': item[0], 'price': item[1]} for item in cart_items]

        conn.close()
        return render_template('profile.html', user=user, user_questions=user_questions, user_answers=user_answers, cart_items=cart_items)
    return redirect(url_for('login'))

@app.route('/cart')
def cart():
    if 'user' in session:
        user = session['user']
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE name = ?', (user,))
        user_id = cursor.fetchone()[0]
        cursor.execute('SELECT * FROM cart_items WHERE user_id = ?', (user_id,))
        cart_items = cursor.fetchall()
        conn.close()
        return render_template('cart.html', cart_items=cart_items)
    return redirect(url_for('login'))

@app.route('/cart/add', methods=['POST'])
def add_to_cart():
    if 'user' in session:
        user = session['user']
        data = request.json
        product_name = data['name']
        price = data['price']

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE name = ?', (user,))
        user_id = cursor.fetchone()[0]
        cursor.execute('INSERT INTO cart_items (user_id, product_name, price) VALUES (?, ?, ?)', (user_id, product_name, price))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Item added to cart'})
    return jsonify({'message': 'User not logged in'}), 401



@app.route('/cart/remove', methods=['POST'])
def remove_from_cart():
    if 'user' in session:
        user = session['user']
        data = request.json
        item_id = data['item_id']

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM cart_items WHERE id = ?', (item_id,))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Item removed from cart'})
    return jsonify({'message': 'User not logged in'}), 401

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        
        # Predict the uploaded image
        prediction_confidence, class_name = predict_image(file_path)
        
        # Pass the results to the result page
        return render_template(
            'result.html', 
            prediction=round(prediction_confidence * 100, 2),  # Convert to percentage
            class_name=class_name
        )


def predict_image(img_path):
    # Load the image and preprocess it
    img = load_img(img_path, target_size=(img_height, img_width))
    img_array = img_to_array(img) / 255.0  # Normalize to [0, 1]
    img_array = np.expand_dims(img_array, axis=0)  # Add batch dimension

    # Get prediction probabilities
    predictions = model.predict(img_array)
    predicted_class_idx = np.argmax(predictions, axis=1)[0]
    predicted_class_name = class_names[predicted_class_idx]
    prediction_confidence = predictions[0][predicted_class_idx]

    return prediction_confidence, predicted_class_name


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
