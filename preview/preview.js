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
})();
