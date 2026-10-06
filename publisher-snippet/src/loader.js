/**
 * Publisher embed snippet.
 *
 * Usage:
 *   <div data-ad-unit-id="123"></div>
 *   <script src="https://your-ad-server.example.com/loader.min.js"
 *           data-api-key="PUBLISHER_API_KEY"
 *           data-server="https://your-ad-server.example.com"></script>
 */
(function () {
  "use strict";

  var memoryVisitorId = null;

  var currentScript = document.currentScript;
  if (!currentScript) {
    var scripts = document.getElementsByTagName("script");
    currentScript = scripts[scripts.length - 1];
  }
  if (!currentScript) return;

  var apiKey = currentScript.getAttribute("data-api-key");
  var serverUrl = currentScript.getAttribute("data-server");
  if (!apiKey || !serverUrl) {
    console.error("[ad-loader] Missing data-api-key or data-server attribute.");
    return;
  }

  serverUrl = serverUrl.replace(/\/+$/, "");


  function getPageContext() {
    var keywords = document.querySelector('meta[name="keywords"]');
    return {
      country: null,
      device_type: /Mobi|Android/i.test(navigator.userAgent) ? "mobile" : "desktop",
      page_keywords: keywords && keywords.content
        ? keywords.content.split(",").map(function (keyword) {
            return keyword.trim();
          })
        : []
    };
  }

  function renderCreative(container, ad) {
    if (!ad || !ad.asset_url || !ad.click_url) {
      console.error("[ad-loader] Received an invalid ad response.", ad);
      return null;
    }

    container.innerHTML = "";
    container.style.display = "";

    var link = document.createElement("a");
    link.href = ad.click_url;
    link.target = "_blank";
    link.rel = "noopener sponsored";

    var image = document.createElement("img");
    image.src = ad.asset_url;
    image.alt = ad.alt_text || "Advertisement";
    image.loading = "lazy";
    image.style.maxWidth = "100%";
    image.style.height = "auto";
    if (Number(ad.width) > 0) image.width = Number(ad.width);
    if (Number(ad.height) > 0) image.height = Number(ad.height);

    link.appendChild(image);
    container.appendChild(link);
    if (ad.creative_id != null) container.dataset.creativeId = ad.creative_id;
    if (ad.campaign_id != null) container.dataset.campaignId = ad.campaign_id;
    return link;
  }

  function getVisitorId() {
    var storageKey = "ad-platform-reporter-id";
    try {
      var existing = window.localStorage.getItem(storageKey);
      if (existing) return existing;
      var visitorId = window.crypto && window.crypto.randomUUID
        ? window.crypto.randomUUID()
        : "visitor-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2);
      window.localStorage.setItem(storageKey, visitorId);
      return visitorId;
    } catch (error) {
      if (!memoryVisitorId) {
        memoryVisitorId = "visitor-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2);
      }
      return memoryVisitorId;
    }
  }

  function addReportControl(container, socket, adUnitId, ad) {
    if (!ad.creative_id) return;

    var details = document.createElement("details");
    details.style.marginTop = "4px";

    var summary = document.createElement("summary");
    summary.textContent = "Report this ad";
    summary.style.cursor = "pointer";
    summary.style.fontSize = "12px";
    details.appendChild(summary);

    var controls = document.createElement("div");
    controls.style.display = "flex";
    controls.style.gap = "6px";
    controls.style.alignItems = "center";
    controls.style.marginTop = "4px";

    var reason = document.createElement("select");
    reason.setAttribute("aria-label", "Why are you reporting this ad?");
    [
      ["", "Choose a reason"],
      ["misleading", "Misleading"],
      ["adult_content", "Adult or 18+ content"],
      ["inappropriate", "Inappropriate"],
      ["scam", "Scam or suspicious"],
      ["other", "Other"]
    ].forEach(function (optionData) {
      var option = document.createElement("option");
      option.value = optionData[0];
      option.textContent = optionData[1];
      reason.appendChild(option);
    });

    var submit = document.createElement("button");
    submit.type = "button";
    submit.textContent = "Submit report";

    var message = document.createElement("span");
    message.setAttribute("role", "status");
    message.style.fontSize = "12px";

    submit.addEventListener("click", function () {
      if (!reason.value) {
        message.textContent = "Choose a reason first.";
        return;
      }

      submit.disabled = true;
      message.textContent = "Sending...";
      socket.emit("report_ad", {
        ad_unit_id: adUnitId,
        creative_id: ad.creative_id,
        api_key: apiKey,
        visitor_id: getVisitorId(),
        reason: reason.value
      }, function (response) {
        message.textContent = response && response.message
          ? response.message
          : "Could not submit the report. Please try again.";
        if (!response || !response.ok) submit.disabled = false;
      });
    });

    controls.appendChild(reason);
    controls.appendChild(submit);
    controls.appendChild(message);
    details.appendChild(controls);
    container.appendChild(details);
  }

  function requestAdForSlot(socket, container) {
    var adUnitId = container.getAttribute("data-ad-unit-id");
    if (!adUnitId || container.getAttribute("data-ad-loading") === "true") return;
    container.setAttribute("data-ad-loading", "true");

    function cleanup() {
      socket.off("serve_ad", onServeAd);
      socket.off("no_fill", onNoFill);
    }

    function onServeAd(ad) {
      cleanup();
      container.removeAttribute("data-ad-loading");
      var link = renderCreative(container, ad);
      if (!link) return;

      link.addEventListener("click", function () {
        socket.emit("click", {
          ad_unit_id: adUnitId,
          creative_id: ad.creative_id
        });
      });
      socket.emit("impression", {
        ad_unit_id: adUnitId,
        creative_id: ad.creative_id
      });
      addReportControl(container, socket, adUnitId, ad);
    }

    function onNoFill() {
      cleanup();
      container.removeAttribute("data-ad-loading");
      container.style.display = "none";
    }

    socket.on("serve_ad", onServeAd);
    socket.on("no_fill", onNoFill);
    socket.emit("request_ad", {
      ad_unit_id: adUnitId,
      api_key: apiKey,
      context: getPageContext()
    });
  }

  function init() {
    if (!window.io) {
      console.error("[ad-loader] Socket.IO client did not initialize.");
      return;
    }

    var socket = window.io(serverUrl + "/delivery", { transports: ["websocket"] });
    socket.on("connect_error", function (error) {
      console.error("[ad-loader] Connection error:", error.message);
    });

    var slots = document.querySelectorAll("[data-ad-unit-id]");
    for (var i = 0; i < slots.length; i += 1) {
      requestAdForSlot(socket, slots[i]);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

})();
