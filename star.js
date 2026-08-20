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

  function markBusy(btn, starring) {
    btn.textContent = starring ? "在标…" : "取消中…";
    btn.disabled = true;
  }

  function post(action, id, title) {
    return fetch((API || "") + "/star", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: action,
        who: who,
        date: date,
        id: id,
        title: title || ""
      })
    }).then(function (res) {
      if (!res.ok) throw new Error("star failed");
      return res.json().catch(function () { return {}; });
    });
  }

  var buttons = document.querySelectorAll("button.star-btn");
  for (var i = 0; i < buttons.length; i++) {
    (function (btn) {
      var id = btn.getAttribute("data-id");
      var title = btn.getAttribute("data-title") || "";
      if (!id) return;
      var starred = false;
      try { starred = !!localStorage.getItem(storageKey(id)); } catch (e) {}
      if (starred) markStarred(btn);
      btn.addEventListener("click", function () {
        if (btn.disabled) return;
        var nowStarred = btn.classList.contains("starred");
        markBusy(btn, !nowStarred);
        post(nowStarred ? "unstar" : "star", id, title).then(function () {
          try {
            if (nowStarred) localStorage.removeItem(storageKey(id));
            else localStorage.setItem(storageKey(id), "1");
          } catch (e) {}
          if (nowStarred) markIdle(btn);
          else markStarred(btn);
        }).catch(function () {
          if (nowStarred) markStarred(btn);
          else markIdle(btn);
          btn.textContent = nowStarred ? "取消失败，再点" : "再点一次";
        });
      });
    })(buttons[i]);
  }
})();
