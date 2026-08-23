/**
 * flyrank-widget-platform embeddable loader (v1)
 *
 * This is the ONLY file a customer's website ever loads. It:
 *   1. Reads its own <script> tag's URL to find the widget id and figure out
 *      which API to talk to (no hardcoded domain — works on any customer site
 *      unmodified, because the URL points back at whoever is hosting this file).
 *   2. Fetches that widget's public config.
 *   3. Renders a minimal form.
 *   4. Wires the submit to POST /submissions (built in Phase 4).
 *
 * Deliberately vanilla JS, no build step, no dependencies — this file IS the
 * product's front door, so it has to load fast and work everywhere.
 */
(function () {
  "use strict";

  var scriptEl =
    document.currentScript ||
    (function () {
      var scripts = document.getElementsByTagName("script");
      return scripts[scripts.length - 1];
    })();

  var scriptUrl = new URL(scriptEl.src);
  var apiBase = scriptUrl.origin;
  var widgetId = scriptUrl.searchParams.get("id");

  if (!widgetId) {
    console.error("[flyrank-widget] Missing ?id=... on the script tag src.");
    return;
  }

  function createContainer() {
    var container = document.createElement("div");
    container.id = "flyrank-widget-" + widgetId;
    container.className = "flyrank-widget";
    scriptEl.parentNode.insertBefore(container, scriptEl.nextSibling);
    return container;
  }

  function renderForm(container, widgetConfig) {
    var fields = (widgetConfig.config && widgetConfig.config.fields) || ["email"];
    var buttonText = (widgetConfig.config && widgetConfig.config.button_text) || "Submit";
    // Generated once, before the first submit attempt. A retried request
    // (flaky network, accidental double-click) reuses this same key, so the
    // server stores the submission exactly once no matter how many times it
    // arrives. See DESIGN.md § 4.
    var idempotencyKey =
      (window.crypto && window.crypto.randomUUID) ? window.crypto.randomUUID() : String(Date.now()) + Math.random();

    var form = document.createElement("form");
    form.setAttribute("novalidate", "true");

    if (widgetConfig.title) {
      var heading = document.createElement("h3");
      heading.textContent = widgetConfig.title;
      container.appendChild(heading);
    }

    fields.forEach(function (fieldName) {
      var label = document.createElement("label");
      label.textContent = fieldName;
      var input = document.createElement("input");
      input.type = fieldName.toLowerCase().indexOf("email") !== -1 ? "email" : "text";
      input.name = fieldName;
      input.required = true;
      label.appendChild(input);
      form.appendChild(label);
    });

    // Honeypot: invisible to real visitors, irresistible to naive bots.
    // The server-side check that acts on this ships in Phase 4 — the field
    // exists from day one so we're not retrofitting the widget markup later.
    var honeypot = document.createElement("input");
    honeypot.type = "text";
    honeypot.name = "hp_field";
    honeypot.tabIndex = -1;
    honeypot.autocomplete = "off";
    honeypot.style.cssText = "position:absolute;left:-9999px;opacity:0;height:0;width:0;";
    form.appendChild(honeypot);

    var button = document.createElement("button");
    button.type = "submit";
    button.textContent = buttonText;
    form.appendChild(button);

    var statusEl = document.createElement("p");
    statusEl.className = "flyrank-widget-status";
    form.appendChild(statusEl);

    form.addEventListener("submit", function (event) {
      event.preventDefault();

      var formData = new FormData(form);
      var payload = { widget_id: widgetId, fields: {}, honeypot: "", idempotency_key: idempotencyKey };
      formData.forEach(function (value, key) {
        if (key === "hp_field") {
          payload.honeypot = value;
        } else {
          payload.fields[key] = value;
        }
      });

      statusEl.textContent = "Sending...";
      button.disabled = true;

      fetch(apiBase + "/submissions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
        .then(function (resp) {
          if (resp.ok) {
            statusEl.textContent = "Thanks! We got it.";
            form.reset();
          } else {
            statusEl.textContent = "Something went wrong. Please try again.";
          }
        })
        .catch(function () {
          statusEl.textContent = "Network error. Please try again.";
        })
        .finally(function () {
          button.disabled = false;
        });
    });

    container.appendChild(form);
  }

  var container = createContainer();

  fetch(apiBase + "/widgets/" + widgetId + "/config")
    .then(function (resp) {
      if (!resp.ok) {
        throw new Error("config fetch failed: " + resp.status);
      }
      return resp.json();
    })
    .then(function (widgetConfig) {
      renderForm(container, widgetConfig);
    })
    .catch(function (err) {
      // Fail silently on the page (don't show a broken widget), but log loudly
      // for the customer's own developer console.
      console.error("[flyrank-widget] Failed to load widget config:", err);
    });
})();
