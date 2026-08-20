(function () {
  "use strict";

  var REPO = "dtu2026/daily-papers";
  var PAGES = "https://dtu2026.github.io/daily-papers";

  var body = document.body;
  if (!body) return;
  var who = body.getAttribute("data-who");
  var date = body.getAttribute("data-date");
  if (!who || !date) return;

  function storageKey(id) {
    return "star:" + who + ":" + date + ":" + id;
  }

  function shortTitle(title) {
    return String(title || "").replace(/^\d+\.\s+/, "").trim();
  }

  function issueUrl(id, title) {
    var issueTitle = "[精读] " + who + " " + date + " " + id + " " + shortTitle(title);
    var paperUrl = PAGES + "/" + who + "/" + date + ".html#" + id;
    var bodyText = [
      "who=" + who,
      "date=" + date,
      "id=" + id,
      "title=" + title,
      "url=" + paperUrl
    ].join("\n");
    return "https://github.com/" + REPO + "/issues/new?title=" +
      encodeURIComponent(issueTitle) +
      "&body=" + encodeURIComponent(bodyText);
  }

  function markStarred(btn) {
    btn.textContent = "★ 已标";
    btn.classList.add("starred");
    btn.setAttribute("aria-pressed", "true");
  }

  var buttons = document.querySelectorAll("button.star-btn");
  for (var i = 0; i < buttons.length; i++) {
    (function (btn) {
      var id = btn.getAttribute("data-id");
      var title = btn.getAttribute("data-title") || "";
      if (!id) return;
      var starred = false;
      try {
        starred = !!localStorage.getItem(storageKey(id));
      } catch (e) {
        starred = false;
      }
      if (starred) markStarred(btn);
      btn.addEventListener("click", function () {
        var already = btn.classList.contains("starred");
        try {
          localStorage.setItem(storageKey(id), "1");
        } catch (e) {}
        markStarred(btn);
        if (!already) {
          window.open(issueUrl(id, title), "_blank", "noopener");
        }
      });
    })(buttons[i]);
  }
})();
