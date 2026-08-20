(function () {
  "use strict";

  var API = window.STAR_API || "";
  var body = document.body;
  if (!body) return;
  var who = body.getAttribute("data-who");
  var date = body.getAttribute("data-date");
  if (!who || !date) return;

  function storageKey(id) {
    return "star:" + who + ":" + date + ":" + id;
  }

  function markStarred(btn) {
    btn.textContent = "★ 已标";
    btn.classList.add("starred");
    btn.setAttribute("aria-pressed", "true");
    btn.disabled = false;
    btn.title = "再点取消";
  }

  function markIdle(btn) {
    btn.textContent = "☆ 想精读";
    btn.classList.remove("starred");
    btn.setAttribute("aria-pressed", "false");
    btn.disabled = false;
    btn.title = "";
  }

  function persist(id, starred) {
    try {
      if (starred) localStorage.setItem(storageKey(id), "1");
      else localStorage.removeItem(storageKey(id));
    } catch (e) {}
  }

  function notify(action, id, title) {
    var q = "action=" + encodeURIComponent(action) +
      "&who=" + encodeURIComponent(who) +
      "&date=" + encodeURIComponent(date) +
      "&id=" + encodeURIComponent(id) +
      "&title=" + encodeURIComponent(title || "");
    var url = (API || "") + "/star?" + q;
    try { new Image().src = url; } catch (e) {}
    if (typeof fetch === "function") {
      var ctrl = typeof AbortController === "function" ? new AbortController() : null;
      var t = ctrl ? setTimeout(function () { ctrl.abort(); }, 4000) : null;
      fetch((API || "") + "/star", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: action, who: who, date: date, id: id, title: title || "" }),
        signal: ctrl ? ctrl.signal : undefined
      }).catch(function () {}).then(function () { if (t) clearTimeout(t); });
    }
  }

  var buttons = document.querySelectorAll("button.star-btn");
  for (var i = 0; i < buttons.length; i++) {
    (function (btn) {
      var id = btn.getAttribute("data-id");
      var title = btn.getAttribute("data-title") || "";
      if (!id) return;
      var starred = false;
      try { starred = !!localStorage.getItem(storageKey(id)); } catch (e) {}
      if (starred) markStarred(btn); else markIdle(btn);
      btn.addEventListener("click", function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        var nowStarred = btn.classList.contains("starred");
        var next = !nowStarred;
        persist(id, next);
        if (next) markStarred(btn); else markIdle(btn);
        notify(next ? "star" : "unstar", id, title);
      });
    })(buttons[i]);
  }
})();
