from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('join_room')
def handle_join(data):
    join_room(data['room'])

@socketio.on('send_message')
def handle_message(data):
    emit('receive_message', data, room=data['room'])

# if __name__ == '__main__':
#     socketio.run(app, debug=True)
if __name__ == '__main__':
        socketio.run(app, host="0.0.0.0", port=10000)