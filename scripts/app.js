async function sendMessage() {
    const input = document.getElementById("user-input").value;
    const responseDiv = document.getElementById("response");

    const res = await fetch("http://127.0.0.1:5000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: input })
    });

    const data = await res.json();
    responseDiv.innerText = `DeenGPT: ${data.response}`;
}
