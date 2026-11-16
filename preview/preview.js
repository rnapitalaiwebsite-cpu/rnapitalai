// Board preview interactions. Nothing is saved or sent: every action is local to the page.
(function () {
  // Tabs
  document.querySelectorAll(".tabs").forEach(function (tabs) {
    var buttons = tabs.querySelectorAll("button[role=tab]");
    function show(btn) {
      buttons.forEach(function (b) {
        var on = b === btn;
        b.setAttribute("aria-selected", on ? "true" : "false");
        document.getElementById(b.getAttribute("aria-controls")).hidden = !on;
      });
    }
    buttons.forEach(function (b) { b.addEventListener("click", function () { show(b); }); });
    var start = location.hash && tabs.querySelector('[data-hash="' + location.hash.slice(1) + '"]');
    show(start || buttons[0]);
  });

  // Engineer app: clock in / out
  var clockBtn = document.getElementById("clock-btn");
  if (clockBtn) {
    clockBtn.addEventListener("click", function () {
      var state = document.getElementById("clock-state");
      var out = clockBtn.classList.toggle("in");
      clockBtn.textContent = out ? "Clock in" : "Clock out";
      state.textContent = out ? "Clocked out at 4:30 pm · 8 hrs 48 min today" : "Clocked in · Sean Lemeki, Engineer";
    });
  }

  // Payroll: approve
  var approve = document.getElementById("approve-btn");
  if (approve) {
    approve.addEventListener("click", function () {
      document.getElementById("step-approve").className = "step done";
      document.getElementById("step-approve").innerHTML = "<b>Approve</b>Approved just now";
      document.getElementById("step-pay").className = "step now";
      document.getElementById("pay-status").textContent = "Pay run approved (demo). The bank file and payslips would be produced now.";
      approve.disabled = true;
    });
  }

  // Client portal: sign in and messages
  var signin = document.getElementById("signin");
  if (signin) {
    signin.addEventListener("submit", function (e) {
      e.preventDefault();
      document.getElementById("login-view").hidden = true;
      document.getElementById("portal-view").hidden = false;
      window.scrollTo(0, 0);
    });
  }
  var send = document.getElementById("send-form");
  if (send) {
    send.addEventListener("submit", function (e) {
      e.preventDefault();
      var input = document.getElementById("msg-input");
      var text = input.value.trim();
      if (!text) return;
      var div = document.createElement("div");
      div.className = "msg me";
      var who = document.createElement("b");
      who.textContent = "You · just now";
      div.appendChild(who);
      div.appendChild(document.createElement("br"));
      div.appendChild(document.createTextNode(text));
      document.getElementById("messages").appendChild(div);
      input.value = "";
    });
  }
  // Media and news: live preview, photo picking, upload, publish
  var form = document.getElementById("post-form");
  if (form) {
    var $ = function (id) { return document.getElementById(id); };
    var months = ["January","February","March","April","May","June","July","August","September","October","November","December"];
    function sync() {
      $("pv-title").textContent = $("sh-title").textContent = $("f-title").value || "Untitled post";
      $("pv-summary").textContent = $("sh-summary").textContent = $("f-summary").value;
      var d = $("f-date").value.split("-");
      var when = d.length === 3 ? (+d[2]) + " " + months[+d[1] - 1] + " " + d[0] : "";
      $("pv-meta").textContent = when + " · " + $("f-type").value;
    }
    ["f-title","f-summary","f-date","f-type"].forEach(function (id) { $(id).addEventListener("input", sync); $(id).addEventListener("change", sync); });
    function usePhoto(src) { $("pv-img").src = src; $("sh-img").src = src; }
    function selectPick(btn) {
      document.querySelectorAll(".pick-img").forEach(function (b) { b.classList.toggle("on", b === btn); });
      usePhoto(btn.getAttribute("data-src"));
    }
    document.querySelectorAll(".pick-img").forEach(function (b) { b.addEventListener("click", function () { selectPick(b); }); });
    $("f-upload").addEventListener("change", function () {
      var f = this.files && this.files[0]; if (!f) return;
      var url = URL.createObjectURL(f);
      var b = document.createElement("button"); b.type = "button"; b.className = "pick-img"; b.setAttribute("data-src", url);
      var im = document.createElement("img"); im.src = url; im.alt = "Your uploaded photo"; b.appendChild(im);
      b.addEventListener("click", function () { selectPick(b); });
      $("pick").insertBefore(b, $("pick").lastElementChild); selectPick(b);
    });
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      $("publish-steps").hidden = false; $("pub-share").hidden = !$("f-share").checked;
      $("draft-status").textContent = "";
      $("publish-btn").textContent = "Published (demo)"; $("publish-btn").disabled = true;
    });
    $("draft-btn").addEventListener("click", function () { $("draft-status").textContent = "Draft saved (demo). Only signed-in staff can see drafts."; });
  }
  document.querySelectorAll("[data-goto]").forEach(function (b) {
    b.addEventListener("click", function () { var t = document.getElementById(b.getAttribute("data-goto")); if (t) { t.click(); window.scrollTo(0, 0); } });
  });
  var lib = document.getElementById("lib-upload");
  if (lib) {
    lib.addEventListener("change", function () {
      Array.prototype.forEach.call(this.files || [], function (f) {
        var fig = document.createElement("figure"); fig.className = "new";
        var im = document.createElement("img"); im.src = URL.createObjectURL(f); im.alt = "";
        var cap = document.createElement("figcaption"); cap.textContent = "Just uploaded (demo, not saved)";
        fig.appendChild(im); fig.appendChild(cap);
        document.getElementById("library").insertBefore(fig, document.getElementById("library").firstChild);
      });
    });
  }
})();
