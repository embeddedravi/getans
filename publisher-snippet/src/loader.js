/**
 * Publisher embed snippet.
 *
 * Usage on a publisher page:
 *
 *   <div id="ad-slot-1" data-ad-unit-id="123"></div>
 *   <script src="https://your-ad-server.example.com/loader.min.js"
 *           data-api-key="PUBLISHER_API_KEY"
 *           data-server="https://your-ad-server.example.com"></script>
 *
 * The loader finds every element with [data-ad-unit-id], connects once to
 * the /delivery Socket.IO namespace, and requests + renders an ad for each.
 */

(function () {
  "use strict";

  var currentScript = document.currentScript;
  var apiKey = currentScript.getAttribute("data-api-key");
  var serverUrl = currentScript.getAttribute("data-server");

  if (!apiKey || !serverUrl) {
    console.error("[ad-loader] Missing data-api-key or data-server attribute.");
    return;
  }

  function loadSocketIoClient(callback) {
    if (window.io) {
      callback();
      return;
    }
    var script = document.createElement("script");
    script.src = serverUrl.replace(/\/$/, "") + "/socket.io/socket.io.js";
    script.onload = callback;
    script.onerror = function () {
      console.error("[ad-loader] Failed to load Socket.IO client.");
    };
    document.head.appendChild(script);
  }

  function getPageContext() {
    return {
      country: null, // optionally set server-side via IP geolocation instead
      device_type: /Mobi|Android/i.test(navigator.userAgent) ? "mobile" : "desktop",
      page_keywords: (document.querySelector('meta[name="keywords"]') || {}).content
        ? document.querySelector('meta[name="keywords"]').content.split(",").map(function (s) {
            return s.trim();
          })
        : [],
    };
  }

  function renderCreative(container, ad) {
    container.innerHTML = "";

    var link = document.createElement("a");
    link.href = ad.click_url;
    link.target = "_blank";
    link.rel = "noopener sponsored";

    var img = document.createElement("img");
    img.src = ad.asset_url;
    img.width = ad.width;
    img.height = ad.height;
    img.alt = "Advertisement";
    img.loading = "lazy";

    link.appendChild(img);
    container.appendChild(link);

    container.dataset.creativeId = ad.creative_id;
    container.dataset.campaignId = ad.campaign_id;

    return link;
  }

  function attachClickTracking(link, socket, adUnitId, ad) {
    link.addEventListener("click", function () {
      socket.emit("click", {
        ad_unit_id: adUnitId,
        creative_id: ad.creative_id,
      });
    });
  }

  function requestAdForSlot(socket, container) {
    var adUnitId = container.getAttribute("data-ad-unit-id");
    if (!adUnitId) return;

    function onServeAd(ad) {
      var link = renderCreative(container, ad);
      attachClickTracking(link, socket, adUnitId, ad);
      socket.emit("impression", {
        ad_unit_id: adUnitId,
        creative_id: ad.creative_id,
      });
      socket.off("serve_ad", onServeAd);
      socket.off("no_fill", onNoFill);
    }

    function onNoFill() {
      container.style.display = "none";
      socket.off("serve_ad", onServeAd);
      socket.off("no_fill", onNoFill);
    }

    socket.on("serve_ad", onServeAd);
    socket.on("no_fill", onNoFill);

    socket.emit("request_ad", {
      ad_unit_id: adUnitId,
      api_key: apiKey,
      context: getPageContext(),
    });
  }

  function init() {
    var socket = window.io(serverUrl + "/delivery", { transports: ["websocket"] });

    socket.on("connect_error", function (err) {
      console.error("[ad-loader] Connection error:", err.message);
    });

    var slots = document.querySelectorAll("[data-ad-unit-id]");
    slots.forEach(function (slot) {
      requestAdForSlot(socket, slot);
    });
  }

  loadSocketIoClient(init);
})();
