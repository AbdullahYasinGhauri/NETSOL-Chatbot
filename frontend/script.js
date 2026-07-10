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