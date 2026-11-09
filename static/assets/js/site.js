// Mobile menu, project filter and enquiry form.
(function () {
  // Mobile menu
  var toggle = document.querySelector(".nav-toggle");
  if (toggle) {
    toggle.addEventListener("click", function () {
      var open = document.body.classList.toggle("nav-open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  // Project filter
  var chips = document.querySelectorAll(".filters .chip");
  chips.forEach(function (chip) {
    chip.addEventListener("click", function () {
      var f = chip.getAttribute("data-filter");
      chips.forEach(function (c) {
        var on = c === chip;
        c.classList.toggle("is-active", on);
        c.setAttribute("aria-pressed", on ? "true" : "false");
      });
      document.querySelectorAll("#project-grid .project-card").forEach(function (card) {
        card.hidden = !(f === "all" || card.getAttribute("data-sector") === f);
      });
    });
  });

  // Enquiry form
  // data-endpoint is set by build.py from content/settings.json:
  //   a URL   -> posts there (Web3Forms or a handler on RNL's own server)
  //   netlify -> posts to Netlify Forms
  //   empty   -> opens the visitor's email app with the enquiry filled in,
  //              so no enquiry is ever lost.
  var form = document.getElementById("enquiry-form");
  if (!form) return;
  var status = form.querySelector(".form-status");
  var button = form.querySelector('button[type="submit"]');

  function setStatus(msg, kind) {
    status.textContent = msg;
    status.className = "form-status" + (kind ? " " + kind : "");
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var bad = [];
    form.querySelectorAll("[required]").forEach(function (el) {
      var ok = el.value.trim() !== "" && (el.type !== "email" || /.+@.+\..+/.test(el.value));
      el.classList.toggle("invalid", !ok);
      el.setAttribute("aria-invalid", ok ? "false" : "true");
      if (!ok) bad.push(el);
    });
    if (bad.length) {
      setStatus("Please fill in your name, a valid email and a short message.", "err");
      bad[0].focus();
      return;
    }
    if (form.botcheck && form.botcheck.value) return; // spam trap

    if (form.getAttribute("data-preview") === "1") {
      setStatus("This is the staging site, so enquiries are not sent. On the live site this goes straight to RNL.", "ok");
      return;
    }
    var data = new FormData(form);
    var endpoint = form.getAttribute("data-endpoint");

    if (!endpoint) {
      var body = "Name: " + data.get("name") +
        "\nOrganisation: " + (data.get("organisation") || "-") +
        "\nEmail: " + data.get("email") +
        "\nPhone: " + (data.get("phone") || "-") +
        "\nEnquiry type: " + data.get("enquiry_type") +
        "\n\n" + data.get("message");
      window.location.href = "mailto:" + form.getAttribute("data-mailto") +
        "?subject=" + encodeURIComponent("Website enquiry: " + data.get("enquiry_type")) +
        "&body=" + encodeURIComponent(body);
      setStatus("Your email app should open with your enquiry ready to send.", "ok");
      return;
    }

    button.disabled = true;
    setStatus("Sending…");
    var req = endpoint === "netlify"
      ? fetch("/", { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body: new URLSearchParams(data).toString() })
      : fetch(endpoint, { method: "POST", body: data, headers: { Accept: "application/json" } });
    req
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r; })
      .then(function () {
        form.reset();
        setStatus("Thank you. Your enquiry has been sent and we will reply within two working days.", "ok");
      })
      .catch(function () {
        setStatus("Sorry, something went wrong. Please email " + form.getAttribute("data-mailto") + " or call us.", "err");
      })
      .then(function () { button.disabled = false; });
  });
})();
