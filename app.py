from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, join_room, emit
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///flashlink.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# =========================
# MODELS
# =========================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String, unique=True)
    name = db.Column(db.String)
    password = db.Column(db.String)
    signup_ip = db.Column(db.String)
    signup_city = db.Column(db.String)
    created_at = db.Column(db.DateTime, default=datetime.now)


class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    ip = db.Column(db.String)
    browser = db.Column(db.String)
    first_seen = db.Column(db.DateTime)
    last_seen = db.Column(db.DateTime)


class Login(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    ip = db.Column(db.String)
    browser = db.Column(db.String)
    city = db.Column(db.String)
    login_time = db.Column(db.DateTime)


class ChatRoom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user1 = db.Column(db.Integer)
    user2 = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.now)


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chatroom_id = db.Column(db.Integer)
    sender_id = db.Column(db.Integer)
    message = db.Column(db.String)
    timestamp = db.Column(db.DateTime)
    status = db.Column(db.String)


# =========================
# INIT DB
# =========================

def init_db():
    with app.app_context():
        db.create_all()
        print("✅ Tables created")

init_db()


# =========================
# ROUTES
# =========================

@app.route('/')
def index():
    return render_template('index.html')


# ---------- AUTH ----------

@app.route('/check-user', methods=['POST'])
def check_user():
    email = request.json.get("user")
    user = User.query.filter_by(email=email).first()
    return {"exists": user is not None}


@app.route('/register', methods=['POST'])
def register():
    data = request.json

    user = User(
        email=data['user'],
        name=data['name'],
        password=data['password'],
        signup_ip=request.remote_addr,
        signup_city="Unknown"
    )

    db.session.add(user)
    db.session.commit()

    print("✅ USER REGISTERED:", user.email)

    return {"status": "created"}


@app.route('/login', methods=['POST'])
def login():
    data = request.json

    user = User.query.filter_by(email=data['user']).first()

    print("🔥 LOGIN ATTEMPT:", data)

    if user and user.password == data['password']:

        # ---------- LOGIN TRACK ----------
        login_entry = Login(
            user_id=user.id,
            ip=request.remote_addr,
            browser=request.headers.get('User-Agent')[:80],
            city="Unknown",
            login_time=datetime.now()
        )
        db.session.add(login_entry)

        # ---------- DEVICE TRACK ----------
        device = Device.query.filter_by(
            user_id=user.id,
            ip=request.remote_addr
        ).first()

        if device:
            device.last_seen = datetime.now()
        else:
            device = Device(
                user_id=user.id,
                ip=request.remote_addr,
                browser=request.headers.get('User-Agent')[:80],
                first_seen=datetime.now(),
                last_seen=datetime.now()
            )
            db.session.add(device)

        db.session.commit()

        print("✅ LOGIN SUCCESS:", user.email)

        return {"status": "success", "user_id": user.id}

    print("❌ LOGIN FAILED")

    return {"status": "fail"}


# ---------- SEARCH USERS ----------

@app.route('/search', methods=['POST'])
def search():
    query = request.json.get("query", "").lower()

    users = User.query.filter(User.email.like(f"%{query}%")).all()

    result = [
        {"id": u.id, "email": u.email, "name": u.name}
        for u in users
    ]

    return {"users": result}


# ---------- CREATE / GET CHATROOM ----------

@app.route('/create-chat', methods=['POST'])
def create_chat():
    u1 = request.json.get("u1")
    u2 = request.json.get("u2")

    room = ChatRoom.query.filter(
        ((ChatRoom.user1 == u1) & (ChatRoom.user2 == u2)) |
        ((ChatRoom.user1 == u2) & (ChatRoom.user2 == u1))
    ).first()

    if not room:
        room = ChatRoom(user1=u1, user2=u2)
        db.session.add(room)
        db.session.commit()

    return {"room_id": room.id}


# ---------- GET MESSAGES ----------

@app.route('/get-messages', methods=['POST'])
def get_messages():
    room_id = request.json.get("room_id")

    msgs = Message.query.filter_by(chatroom_id=room_id).all()

    return {
        "messages": [
            {
                "user": m.sender_id,
                "message": m.message,
                "time": m.timestamp.strftime("%H:%M"),
                "status": m.status
            }
            for m in msgs
        ]
    }


# =========================
# SOCKET
# =========================

@socketio.on('join')
def handle_join(data):
    join_room(str(data['room']))


@socketio.on('send')
def handle_send(data):

    msg = Message(
        chatroom_id=data['room'],
        sender_id=data['user'],
        message=data['message'],
        timestamp=datetime.now(),
        status="sent"
    )

    db.session.add(msg)
    db.session.commit()

    emit('receive', {
        "user": data['user'],
        "message": data['message'],
        "time": datetime.now().strftime("%H:%M"),
        "status": "sent"
    }, room=str(data['room']))

# =========================
# 📊 POWER BI APIs (ALL TABLES)
# =========================

from flask import jsonify


# ---------- USERS ----------
@app.route('/api/users')
def api_users():
    users = User.query.all()

    return jsonify([
        {
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "signup_ip": u.signup_ip,
            "signup_city": u.signup_city,
            "created_at": str(u.created_at)
        }
        for u in users
    ])


# ---------- DEVICES ----------
@app.route('/api/devices')
def api_devices():
    devices = Device.query.all()

    return jsonify([
        {
            "id": d.id,
            "user_id": d.user_id,
            "ip": d.ip,
            "browser": d.browser,
            "first_seen": str(d.first_seen),
            "last_seen": str(d.last_seen)
        }
        for d in devices
    ])


# ---------- LOGIN HISTORY ----------
@app.route('/api/logins')
def api_logins():
    logins = Login.query.all()

    return jsonify([
        {
            "id": l.id,
            "user_id": l.user_id,
            "ip": l.ip,
            "browser": l.browser,
            "city": l.city,
            "login_time": str(l.login_time)
        }
        for l in logins
    ])


# ---------- CHATROOMS ----------
@app.route('/api/chatrooms')
def api_chatrooms():
    rooms = ChatRoom.query.all()

    return jsonify([
        {
            "id": r.id,
            "user1": r.user1,
            "user2": r.user2,
            "created_at": str(r.created_at)
        }
        for r in rooms
    ])


# ---------- MESSAGES ----------
@app.route('/api/messages')
def api_messages():
    messages = Message.query.all()

    return jsonify([
        {
            "id": m.id,
            "chatroom_id": m.chatroom_id,
            "sender_id": m.sender_id,
            "message": m.message,
            "timestamp": str(m.timestamp),
            "status": m.status
        }
        for m in messages
    ])


# =========================
# 🔥 ADVANCED (JOINED DATA FOR PBI)
# =========================

@app.route('/api/messages-detailed')
def api_messages_detailed():

    data = db.session.query(
        Message,
        User.name
    ).join(User, Message.sender_id == User.id).all()

    return jsonify([
        {
            "message_id": m.id,
            "chatroom_id": m.chatroom_id,
            "sender_name": name,
            "message": m.message,
            "timestamp": str(m.timestamp),
            "status": m.status
        }
        for m, name in data
    ])

# =========================
# RUN
# =========================

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=10000)
# if __name__ == '__main__':
#     socketio.run(app, debug=True)