/*

const API = "http://127.0.0.1:8000";

let currentThread = "";

window.onload = async () => {

    await loadSessions();

    if (document.getElementById("sessions").children.length === 0) {
        await createChat();
    }

};

// ----------------------------
// Create New Chat
// ----------------------------
async function createChat() {

    const res = await fetch(`${API}/new_chat`, {
        method: "POST"
    });

    const data = await res.json();

    currentThread = data.thread_id;

    document.getElementById("chat-box").innerHTML = "";

    await loadSessions();
}

// Called from button
function newChat() {
    createChat();
}

// ----------------------------
// Load Sidebar Sessions
// ----------------------------
async function loadSessions() {

    const res = await fetch(`${API}/sessions`);
    const sessions = await res.json();

    const sidebar = document.getElementById("sessions");
    sidebar.innerHTML = "";

    sessions.forEach(session => {

        sidebar.innerHTML += `
    <div class="session" onclick="openChat('${session.thread_id}')">
        ${session.title}
    </div>
    `;
});

    if (sessions.length > 0 && currentThread === "") {
        openChat(sessions[0].thread_id);
    }
}

// ----------------------------
// Open Existing Chat
// ----------------------------
async function openChat(threadId) {

    currentThread = threadId;

    const res = await fetch(`${API}/messages/${threadId}`);

    const messages = await res.json();

    const chat = document.getElementById("chat-box");

    chat.innerHTML = "";

    messages.forEach(msg => {

        const sender = msg[0];
        const text = msg[1];

        chat.innerHTML += `
            <div class="message ${sender === "user" ? "user" : "bot"}">
                ${text}
            </div>
        `;

    });

    chat.scrollTop = chat.scrollHeight;

}

// ----------------------------
// Send Message
// ----------------------------
async function sendMessage() {

    const input = document.getElementById("question");

    const question = input.value.trim();

    if (question === "") return;

    const chat = document.getElementById("chat-box");

    chat.innerHTML += `
        <div class="message user">
            ${question}
        </div>
    `;

    chat.scrollTop = chat.scrollHeight;

    input.value = "";

    const res = await fetch(`${API}/chat`, {

        method: "POST",

        headers: {
            "Content-Type": "application/json"
        },

        body: JSON.stringify({

            thread_id: currentThread,
            question: question

        })

    });

    const data = await res.json();

    chat.innerHTML += `
        <div class="message bot">
            ${data.answer}
        </div>
    `;

    chat.scrollTop = chat.scrollHeight;

    // Refresh sidebar so title changes
    await loadSessions();

}

// ----------------------------
// Enter Key Support
// ----------------------------
document.getElementById("question").addEventListener("keypress", function(e){

    if(e.key === "Enter"){
        sendMessage();
    }

});
*/

const API = "http://127.0.0.1:8000";

let currentThread = "";

const chatBox = document.getElementById("chat-box");
const sessionsBox = document.getElementById("sessions");
const input = document.getElementById("question");
const sendBtn = document.getElementById("send-btn");

window.onload = async () => {

    await loadSessions();

    if (sessionsBox.children.length === 0) {
        await createChat();
    }

};

async function sendMessage(question) {
  const res = await fetch("http://127.0.0.1:8000/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question })
  });
  const data = await res.json();
  return data.answer;
}

// ----------------------------
// Empty state helper
// ----------------------------
function showEmptyState() {
    chatBox.innerHTML = `
        <div class="empty-state" id="empty-state">
            <div class="empty-mark">N</div>
            <h3>Start the conversation</h3>
            <p>Ask a question and I'll pull the answer from your NETSOL data.</p>
        </div>
    `;
}

// ----------------------------
// Message rendering (safe — no raw HTML injection)
// ----------------------------
function appendMessage(sender, text) {
    const existingEmpty = document.getElementById("empty-state");
    if (existingEmpty) existingEmpty.remove();

    const isUser = sender === "user";

    const row = document.createElement("div");
    row.className = `msg-row ${isUser ? "user" : "bot"}`;

    const avatar = document.createElement("div");
    avatar.className = `avatar ${isUser ? "user-avatar" : "bot-avatar"}`;
    avatar.textContent = isUser ? "U" : "N";

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = text;

    row.appendChild(isUser ? bubble : avatar);
    row.appendChild(isUser ? avatar : bubble);

    chatBox.appendChild(row);
    chatBox.scrollTop = chatBox.scrollHeight;

    return row;
}

function showTypingIndicator() {
    const row = document.createElement("div");
    row.className = "msg-row bot";
    row.id = "typing-indicator";

    row.innerHTML = `
        <div class="avatar bot-avatar">N</div>
        <div class="bubble typing-bubble"><span></span><span></span><span></span></div>
    `;

    chatBox.appendChild(row);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function removeTypingIndicator() {
    const el = document.getElementById("typing-indicator");
    if (el) el.remove();
}

// ----------------------------
// Create New Chat
// ----------------------------
async function createChat() {

    const res = await fetch(`${API}/new_chat`, {
        method: "POST"
    });

    const data = await res.json();

    currentThread = data.thread_id;

    showEmptyState();

    await loadSessions();
}

// Called from button
function newChat() {
    createChat();
}

// ----------------------------
// Load Sidebar Sessions
// ----------------------------
async function loadSessions() {

    const res = await fetch(`${API}/sessions`);
    const sessions = await res.json();

    sessionsBox.innerHTML = "";

    sessions.forEach(session => {
        const item = document.createElement("div");
        item.className = "session" + (session.thread_id === currentThread ? " active" : "");
        item.textContent = session.title;
        item.dataset.threadId = session.thread_id;
        item.tabIndex = 0;
        item.onclick = () => openChat(session.thread_id);
        sessionsBox.appendChild(item);
    });

    if (sessions.length > 0 && currentThread === "") {
        openChat(sessions[0].thread_id);
    }
}

// ----------------------------
// Open Existing Chat
// ----------------------------
async function openChat(threadId) {

    currentThread = threadId;

    const res = await fetch(`${API}/messages/${threadId}`);

    const messages = await res.json();

    chatBox.innerHTML = "";

    if (messages.length === 0) {
        showEmptyState();
    } else {
        messages.forEach(msg => appendMessage(msg[0], msg[1]));
    }

    highlightActiveSession();

}

function highlightActiveSession() {
    [...sessionsBox.children].forEach(el => {
        el.classList.toggle("active", el.dataset.threadId === currentThread);
    });
}

// ----------------------------
// Send Message
// ----------------------------
async function sendMessage() {

    const question = input.value.trim();

    if (question === "") return;

    appendMessage("user", question);

    input.value = "";
    input.focus();
    sendBtn.disabled = true;
    input.disabled = true;

    showTypingIndicator();

    try {

        const res = await fetch(`${API}/chat`, {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({

                thread_id: currentThread,
                question: question

            })

        });

        const data = await res.json();

        removeTypingIndicator();
        appendMessage("bot", data.answer);

    } catch (err) {

        removeTypingIndicator();
        appendMessage("bot", "Something went wrong reaching the server. Please try again.");

    } finally {

        sendBtn.disabled = false;
        input.disabled = false;
        input.focus();

        // Refresh sidebar so title changes
        await loadSessions();

    }

}

// ----------------------------
// Enter Key Support
// ----------------------------
input.addEventListener("keypress", function (e) {

    if (e.key === "Enter") {
        sendMessage();
    }

});