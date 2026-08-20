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
    btn.disabled = true;
  }

  function markBusy(btn) {
    btn.textContent = "在标…";
    btn.disabled = true;
  }

  function markFail(btn) {
    btn.textContent = "再点一次";
    btn.disabled = false;
    btn.classList.remove("starred");
    btn.setAttribute("aria-pressed", "false");
  }

  function postStar(id, title) {
    var endpoint = (API || "") + "/star";
    return fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
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
        if (btn.classList.contains("starred") || btn.disabled) return;
        markBusy(btn);
        postStar(id, title).then(function () {
          try { localStorage.setItem(storageKey(id), "1"); } catch (e) {}
          markStarred(btn);
        }).catch(function () {
          markFail(btn);
        });
      });
    })(buttons[i]);
  }
})();
