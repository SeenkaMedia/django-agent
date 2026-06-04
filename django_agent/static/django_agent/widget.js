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

  var ACTIONS = {
    create: { cls: "create", label: "Crear", verb: "Crear", icon: "＋" },
    update: { cls: "update", label: "Modificar", verb: "Guardar", icon: "✎" },
    delete: { cls: "delete", label: "Borrar", verb: "Borrar", icon: "🗑", danger: true },
  };

  function fmtVal(v) {
    if (v === null || v === undefined || v === "") return "—";
    if (typeof v === "object") return v._str !== undefined ? v._str : JSON.stringify(v);
    return String(v);
  }

  function span(text, cls) {
    var s = document.createElement("span"); s.className = cls; s.textContent = text; return s;
  }

  function kvRow(key, valueNode) {
    var row = document.createElement("div"); row.className = "ag-kv-row";
    row.appendChild(span(key, "ag-k")); row.appendChild(valueNode); return row;
  }

  function diffNode(oldText, newText) {
    var w = document.createElement("span");
    w.appendChild(span(oldText, "ag-old")); w.appendChild(span(" → ", "ag-arrow")); w.appendChild(span(newText, "ag-new"));
    return w;
  }

  function cardBody(p) {
    var box = document.createElement("div"); box.className = "ag-kv";
    if (p.op === "delete") {
      box.appendChild(kvRow(p.model_verbose || "registro", span(fmtVal(p.current) , "ag-v")));
      return box;
    }
    var data = p.data || {};
    Object.keys(data).forEach(function (k) {
      var nv = fmtVal(data[k]);
      if (p.op === "update" && p.current && k in p.current) {
        var ov = fmtVal(p.current[k]);
        box.appendChild(kvRow(k, ov === nv ? span(nv + "  (sin cambios)", "ag-same") : diffNode(ov, nv)));
      } else {
        box.appendChild(kvRow(k, span(nv, "ag-new")));
      }
    });
    return box;
  }

  function confirmCard(c) {
    var p = c.preview || {}, meta = ACTIONS[c.op] || { cls: "", label: c.op, verb: "Confirmar", icon: "•" };
    var card = document.createElement("div"); card.className = "ag-card " + meta.cls;
    var title = p.model_verbose || p.model || "";
    if (p.pk) title += " #" + p.pk;
    card.appendChild(span(meta.icon + " " + meta.label + " · " + title, "ag-card-head"));
    card.appendChild(cardBody(p));
    if (meta.danger) card.appendChild(span("⚠ Esta acción no se puede deshacer.", "ag-warn"));
    var actions = document.createElement("div"); actions.className = "ag-actions";
    var ok = document.createElement("button"); ok.className = "ag-ok" + (meta.danger ? " danger" : ""); ok.textContent = meta.verb;
    var no = document.createElement("button"); no.className = "ag-no"; no.textContent = "Cancelar";
    actions.appendChild(ok); actions.appendChild(no);
    card.appendChild(actions);
    el.msgs.appendChild(card); scroll();
    ok.addEventListener("click", function () { resolve(card, true); });
    no.addEventListener("click", function () { resolve(card, false); });
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
