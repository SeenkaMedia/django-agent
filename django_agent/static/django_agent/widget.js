(function () {
  "use strict";
  var root = document.getElementById("agent-root");
  if (!root) return;
  var URLS = { history: root.dataset.history, message: root.dataset.message, confirm: root.dataset.confirm };

  function csrf() {
    var m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? m[1] : "";
  }

  function post(url, body) {
    return fetch(url, {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() },
      body: JSON.stringify(body),
    }).then(function (r) { return r.json(); });
  }

  function pageContext() {
    var path = location.pathname;
    var ctx = { url: path + location.search, title: document.title };
    var mm = path.match(/\/admin\/(\w+)\/(\w+)\//);
    if (mm) { ctx.app = mm[1]; ctx.model = mm[1] + "." + mm[2]; }
    var pk = path.match(/\/(\d+)\/change\//);
    if (pk && ctx.model) ctx.object = { model: ctx.model, pk: pk[1] };
    return ctx;
  }

  var el = {};
  function build() {
    var btn = document.createElement("button");
    btn.className = "ag-btn"; btn.title = "Asistente";
    if (root.dataset.logo) {
      var logo = document.createElement("img");
      logo.src = root.dataset.logo; logo.alt = "Asistente"; logo.className = "ag-logo";
      btn.appendChild(logo);
    } else {
      btn.textContent = "💬";
    }
    var panel = document.createElement("div");
    panel.className = "ag-panel";
    panel.innerHTML =
      '<div class="ag-head"><span>Asistente</span><span class="ag-x">✕</span></div>' +
      '<div class="ag-msgs"></div>' +
      '<div class="ag-foot"><textarea placeholder="Escribí algo…"></textarea><button class="ag-send">➤</button></div>';
    root.appendChild(btn); root.appendChild(panel);
    el = {
      btn: btn, panel: panel, msgs: panel.querySelector(".ag-msgs"),
      input: panel.querySelector("textarea"), send: panel.querySelector(".ag-send"),
      x: panel.querySelector(".ag-x"),
    };
    btn.addEventListener("click", toggle);
    el.x.addEventListener("click", toggle);
    el.send.addEventListener("click", onSend);
    el.input.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); onSend(); }
    });
  }

  function toggle() {
    var open = el.panel.classList.toggle("open");
    localStorage.setItem("agentOpen", open ? "1" : "0");
    if (open) loadHistory();
  }

  function bubble(cls, text) {
    var d = document.createElement("div");
    d.className = "ag-msg " + cls; d.textContent = text;
    el.msgs.appendChild(d); scroll();
    return d;
  }

  function toolNote(op) { bubble("ag-tool", "⚙ " + op); }

  function scroll() { el.msgs.scrollTop = el.msgs.scrollHeight; }

  function render(messages) {
    el.msgs.innerHTML = "";
    messages.forEach(function (m) {
      if (m.role === "user") bubble("ag-user", m.text);
      else if (m.role === "tool_call") toolNote(m.op);
      else if (m.text) bubble("ag-model", m.text);
    });
  }

  function loadHistory() {
    fetch(URLS.history, { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (d) { render(d.messages || []); });
  }

  var busy = false;
  function setBusy(b) { busy = b; el.send.disabled = b; }

  function typing() {
    var d = document.createElement("div");
    d.className = "ag-typing"; d.textContent = "pensando…";
    el.msgs.appendChild(d); scroll();
    return d;
  }

  function handle(res) {
    if (res.reply) bubble("ag-model", res.reply);
    if (res.confirm) confirmCard(res.confirm);
  }

  function onSend() {
    var text = el.input.value.trim();
    if (!text || busy) return;
    el.input.value = ""; bubble("ag-user", text); setBusy(true);
    var t = typing();
    post(URLS.message, { text: text, page_context: pageContext() })
      .then(function (res) { t.remove(); handle(res); })
      .catch(function () { t.remove(); bubble("ag-model", "Error de conexión."); })
      .finally(function () { setBusy(false); });
  }

  function confirmCard(c) {
    var card = document.createElement("div");
    card.className = "ag-card";
    var body = { model: c.preview.model, pk: c.preview.pk, data: c.preview.data, filters: c.preview.filters };
    card.innerHTML = "<h4>Confirmar: " + escapeHtml(String(c.op)) + "</h4><pre>" +
      escapeHtml(JSON.stringify(body, null, 2)) + "</pre>" +
      '<div class="ag-actions"><button class="ag-ok">Confirmar</button><button class="ag-no">Cancelar</button></div>';
    el.msgs.appendChild(card); scroll();
    card.querySelector(".ag-ok").addEventListener("click", function () { resolve(card, true); });
    card.querySelector(".ag-no").addEventListener("click", function () { resolve(card, false); });
  }

  function resolve(card, accept) {
    card.querySelectorAll("button").forEach(function (b) { b.disabled = true; });
    setBusy(true);
    var t = typing();
    post(URLS.confirm, { accept: accept, page_context: pageContext() })
      .then(function (res) { t.remove(); handle(res); })
      .catch(function () { t.remove(); bubble("ag-model", "Error de conexión."); })
      .finally(function () { setBusy(false); });
  }

  function escapeHtml(s) {
    return s.replace(/[&<>]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]; });
  }

  build();
  if (localStorage.getItem("agentOpen") === "1") { el.panel.classList.add("open"); loadHistory(); }
})();
