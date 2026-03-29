const socket = io();

let userData = JSON.parse(localStorage.getItem("user")) || {};
let isExisting = false;
let currentRoom = null;

// AUTO LOGIN
if (userData.id) {
    showApp();
}

// STEP 1
function checkUser() {
    userData.user = document.getElementById("userInput").value;

    fetch('/check-user', {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({user: userData.user})
    })
    .then(res => res.json())
    .then(data => {
        isExisting = data.exists;

        document.getElementById("step1").classList.add("hidden");
        document.getElementById("step2").classList.remove("hidden");

        if (isExisting) {
            document.getElementById("stepTitle").innerText = "Welcome back";
        } else {
            document.getElementById("stepTitle").innerText = "Create account";
            document.getElementById("nameInput").classList.remove("hidden");
        }
    });
}

// STEP 2
function proceedAuth() {
    userData.password = document.getElementById("passwordInput").value;
    userData.name = document.getElementById("nameInput").value;

    if (isExisting) login();
    else register();
}

function register() {
    fetch('/register', {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(userData)
    }).then(() => login());
}

function login() {
    fetch('/login', {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(userData)
    })
    .then(res => res.json())
    .then(data => {
        userData.id = data.user_id;

        localStorage.setItem("user", JSON.stringify(userData));
        showApp();
    });
}

function showApp() {
    document.getElementById("step1").classList.add("hidden");
    document.getElementById("step2").classList.add("hidden");
    document.getElementById("app").classList.remove("hidden");
}

// SEARCH USERS
function searchUser(q) {
    fetch('/search', {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({query: q})
    })
    .then(res => res.json())
    .then(data => {
        const list = document.getElementById("searchResults");
        list.innerHTML = "";

        data.users.forEach(u => {
            const div = document.createElement("div");
            div.innerText = u.name;
            div.onclick = () => openChat(u);
            list.appendChild(div);
        });
    });
}

// OPEN CHAT
function openChat(user) {
    document.getElementById("chatName").innerText = user.name;

    fetch('/create-chat', {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            u1: userData.id,
            u2: user.id
        })
    })
    .then(res => res.json())
    .then(data => {
        currentRoom = data.room_id;

        socket.emit("join", {room: currentRoom});
        loadMessages();

        document.querySelector(".chat-area").classList.add("active");
    });
}

// LOAD MESSAGES
function loadMessages() {
    fetch('/get-messages', {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({room_id: currentRoom})
    })
    .then(res => res.json())
    .then(data => {
        const chat = document.getElementById("messages");
        chat.innerHTML = "";

        data.messages.forEach(addMessage);
    });
}

// SEND
function sendMessage() {
    const msg = document.getElementById("msg").value;

    socket.emit("send", {
        room: currentRoom,
        user: userData.id,
        message: msg
    });

    document.getElementById("msg").value = "";
}

// RECEIVE
socket.on("receive", addMessage);

function addMessage(m) {
    const chat = document.getElementById("messages");

    const div = document.createElement("div");
    div.classList.add("message");

    if (m.user == userData.id) div.classList.add("sent");
    else div.classList.add("received");

    div.innerHTML = `${m.message}<br><small>${m.time}</small>`;

    chat.appendChild(div);
}

// MOBILE BACK
function goBack() {
    document.querySelector(".chat-area").classList.remove("active");
}