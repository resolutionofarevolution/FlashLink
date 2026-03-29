const socket = io();

let username = "";
let room = "general";

function joinChat() {
    username = document.getElementById("username").value;

    if (!username) {
        alert("Enter username");
        return;
    }

    socket.emit("join_room", { room: room });
}

function sendMessage() {
    const msg = document.getElementById("message").value;

    socket.emit("send_message", {
        room: room,
        user: username,
        message: msg
    });

    document.getElementById("message").value = "";
}

socket.on("receive_message", (data) => {
    const chat = document.getElementById("chat");

    chat.innerHTML += `
        <div class="message">
            <b>${data.user}:</b> ${data.message}
        </div>
    `;

    chat.scrollTop = chat.scrollHeight;
});