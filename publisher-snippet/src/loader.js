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
