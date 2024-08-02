import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, send, join_room, leave_room
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, instance_path=os.path.join(basedir, 'instance'))
app.config['SECRET_KEY'] = 'secret!'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance/chat.db')
db = SQLAlchemy(app)
socketio = SocketIO(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    content = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    room = db.Column(db.String(50), nullable=False)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['username'] = username
            print(f"Logged in as {username}")  # デバッグ用
            return redirect(url_for('index'))
        else:
            print("Login failed")  # デバッグ用
    return render_template('login.html')



@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    messages = Message.query.order_by(Message.timestamp.asc()).all()
    return render_template('index.html', messages=messages)

@socketio.on('join')
def on_join(data):
    username = session['username']
    room = data['room']
    join_room(room)
    send(username + ' has entered the room.', to=room)

@socketio.on('leave')
def on_leave(data):
    username = session['username']
    room = data['room']
    leave_room(room)
    send(username + ' has left the room.', to=room)

@socketio.on('message')
def handleMessage(data):
    room = data['room']
    msg = data['msg']
    username = session['username']
    new_message = Message(username=username, content=msg, room=room)
    db.session.add(new_message)
    db.session.commit()
    send(username + ': ' + msg, to=room)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, host='0.0.0.0', port=5000)
