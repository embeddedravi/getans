/**
 * Publisher embed snippet.
 *
 * Usage:
 *   <div data-ad-unit-id="123"></div>
 *   <script src="https://cdn.socket.io/4.8.1/socket.io.min.js"></script>
 *   <script src="https://your-cdn.example.com/loader.js"
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

  function renderPollCreative(container, ad, socket, adUnitId) {
    var attrs = ad.custom_attributes || {};
    var question = attrs.poll_question || ad.poll_question || "Poll Question";
    var options = attrs.poll_options || ad.poll_options || [
      "Option 1", "Option 2", "Option 3", "Option 4"
    ];
    while (options.length < 4) {
      options.push("Option " + (options.length + 1));
    }
    if (options.length > 4) {
      options = options.slice(0, 4);
    }

    container.innerHTML = "";
    container.style.display = "";

    var card = document.createElement("div");
    card.className = "getans-poll-ad";
    var w = Number(ad.width) > 0 ? Number(ad.width) : 300;
    var h = Number(ad.height) > 0 ? Number(ad.height) : 250;
    card.style.position = "relative";
    card.style.display = "flex";
    card.style.flexDirection = "column";
    card.style.justifyContent = "space-between";
    card.style.width = w + "px";
    card.style.maxWidth = "100%";
    card.style.minHeight = h + "px";
    card.style.boxSizing = "border-box";
    card.style.padding = "12px 14px";
    card.style.borderRadius = "10px";
    card.style.fontFamily = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif";
    card.style.background = "linear-gradient(145deg, #18181b 0%, #09090b 100%)";
    card.style.color = "#f4f4f5";
    card.style.border = "1px solid #27272a";
    card.style.boxShadow = "0 4px 16px rgba(0, 0, 0, 0.25)";
    card.style.overflow = "hidden";
    card.style.textAlign = "left";

    // Top Header: Badge + Sponsor Link
    var header = document.createElement("div");
    header.style.display = "flex";
    header.style.alignItems = "center";
    header.style.justifyContent = "space-between";
    header.style.marginBottom = "8px";
    header.style.fontSize = "11px";

    var badge = document.createElement("span");
    badge.textContent = "POLL";
    badge.style.display = "inline-flex";
    badge.style.alignItems = "center";
    badge.style.background = "#6366f1";
    badge.style.color = "#ffffff";
    badge.style.fontSize = "10px";
    badge.style.fontWeight = "700";
    badge.style.letterSpacing = "0.5px";
    badge.style.padding = "2px 7px";
    badge.style.borderRadius = "9999px";
    badge.style.lineHeight = "1.2";

    var sponsorLink = document.createElement("a");
    sponsorLink.href = ad.click_url;
    sponsorLink.target = "_blank";
    sponsorLink.rel = "noopener sponsored";
    sponsorLink.textContent = "Sponsored ↗";
    sponsorLink.style.color = "#a1a1aa";
    sponsorLink.style.textDecoration = "none";
    sponsorLink.style.fontSize = "11px";
    sponsorLink.style.marginRight = "24px"; // space for report control

    header.appendChild(badge);
    header.appendChild(sponsorLink);
    card.appendChild(header);

    // Question
    var questionEl = document.createElement("div");
    questionEl.textContent = question;
    questionEl.style.fontSize = "13px";
    questionEl.style.fontWeight = "600";
    questionEl.style.lineHeight = "1.35";
    questionEl.style.color = "#ffffff";
    questionEl.style.marginBottom = "8px";
    card.appendChild(questionEl);

    // 4 Options container
    var optionsList = document.createElement("div");
    optionsList.style.display = "flex";
    optionsList.style.flexDirection = "column";
    optionsList.style.gap = "5px";
    optionsList.style.flex = "1";
    optionsList.style.justifyContent = "center";

    var letters = ["A", "B", "C", "D"];
    var optionBtns = [];
    var initialStats = ad.poll_results || {
      counts: [0, 0, 0, 0],
      percentages: [0, 0, 0, 0],
      total_votes: 0
    };
    var hasVoted = false;

    function applyResults(results, selectedIdx) {
      hasVoted = true;
      var counts = results.counts || [0, 0, 0, 0];
      var pcts = results.percentages || [0, 0, 0, 0];
      var total = results.total_votes || 0;

      for (var i = 0; i < optionBtns.length; i++) {
        var btn = optionBtns[i];
        btn.disabled = true;
        btn.style.cursor = "default";
        var isSelected = (i === selectedIdx);

        if (isSelected) {
          btn.style.borderColor = "#6366f1";
          btn.style.background = "rgba(99, 102, 241, 0.15)";
        }

        var bar = btn.querySelector(".poll-bar");
        if (bar) {
          bar.style.width = pcts[i] + "%";
          bar.style.background = isSelected
            ? "rgba(99, 102, 241, 0.35)"
            : "rgba(255, 255, 255, 0.1)";
        }
        var pctLabel = btn.querySelector(".poll-pct");
        if (pctLabel) {
          pctLabel.textContent = pcts[i] + "%";
          pctLabel.style.display = "block";
        }
      }

      if (footerStatus) {
        footerStatus.textContent = total + " vote" + (total === 1 ? "" : "s");
      }
      if (ctaBtn) {
        ctaBtn.style.display = "inline-flex";
      }
    }

    options.forEach(function (optText, idx) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "poll-opt-btn";
      btn.style.position = "relative";
      btn.style.display = "flex";
      btn.style.alignItems = "center";
      btn.style.justifyContent = "space-between";
      btn.style.width = "100%";
      btn.style.boxSizing = "border-box";
      btn.style.padding = "6px 8px";
      btn.style.background = "rgba(255, 255, 255, 0.05)";
      btn.style.border = "1px solid rgba(255, 255, 255, 0.12)";
      btn.style.borderRadius = "6px";
      btn.style.color = "#f4f4f5";
      btn.style.cursor = "pointer";
      btn.style.textAlign = "left";
      btn.style.fontSize = "12px";
      btn.style.overflow = "hidden";
      btn.style.transition = "all 0.2s ease";

      var bar = document.createElement("div");
      bar.className = "poll-bar";
      bar.style.position = "absolute";
      bar.style.top = "0";
      bar.style.left = "0";
      bar.style.bottom = "0";
      bar.style.width = "0%";
      bar.style.transition = "width 0.5s cubic-bezier(0.4, 0, 0.2, 1)";
      bar.style.zIndex = "1";
      btn.appendChild(bar);

      var contentWrapper = document.createElement("div");
      contentWrapper.style.position = "relative";
      contentWrapper.style.zIndex = "2";
      contentWrapper.style.display = "flex";
      contentWrapper.style.alignItems = "center";
      contentWrapper.style.gap = "6px";
      contentWrapper.style.overflow = "hidden";
      contentWrapper.style.textOverflow = "ellipsis";
      contentWrapper.style.whiteSpace = "nowrap";

      var letterCircle = document.createElement("span");
      letterCircle.textContent = letters[idx];
      letterCircle.style.display = "inline-flex";
      letterCircle.style.alignItems = "center";
      letterCircle.style.justifyContent = "center";
      letterCircle.style.width = "18px";
      letterCircle.style.height = "18px";
      letterCircle.style.borderRadius = "50%";
      letterCircle.style.background = "rgba(255, 255, 255, 0.12)";
      letterCircle.style.fontSize = "10px";
      letterCircle.style.fontWeight = "600";
      letterCircle.style.flexShrink = "0";

      var label = document.createElement("span");
      label.textContent = optText;
      label.style.overflow = "hidden";
      label.style.textOverflow = "ellipsis";
      label.style.whiteSpace = "nowrap";

      contentWrapper.appendChild(letterCircle);
      contentWrapper.appendChild(label);
      btn.appendChild(contentWrapper);

      var pct = document.createElement("span");
      pct.className = "poll-pct";
      pct.style.position = "relative";
      pct.style.zIndex = "2";
      pct.style.fontSize = "11px";
      pct.style.fontWeight = "600";
      pct.style.display = "none";
      btn.appendChild(pct);

      btn.addEventListener("mouseenter", function () {
        if (!hasVoted) {
          btn.style.background = "rgba(255, 255, 255, 0.1)";
          btn.style.borderColor = "rgba(255, 255, 255, 0.25)";
        }
      });
      btn.addEventListener("mouseleave", function () {
        if (!hasVoted) {
          btn.style.background = "rgba(255, 255, 255, 0.05)";
          btn.style.borderColor = "rgba(255, 255, 255, 0.12)";
        }
      });

      btn.addEventListener("click", function (evt) {
        evt.stopPropagation();
        if (hasVoted) return;
        hasVoted = true;

        var updatedCounts = [].concat(initialStats.counts || [0, 0, 0, 0]);
        updatedCounts[idx] = (updatedCounts[idx] || 0) + 1;
        var total = 0;
        for (var k = 0; k < updatedCounts.length; k++) total += updatedCounts[k];
        var pcts = updatedCounts.map(function (c) {
          return total > 0 ? Math.round((c / total) * 100) : 0;
        });

        applyResults({ counts: updatedCounts, percentages: pcts, total_votes: total }, idx);

        if (socket && ad.serve_token) {
          socket.emit("poll_vote", {
            ad_unit_id: adUnitId,
            creative_id: ad.creative_id,
            visitor_id: ad.visitor_id,
            serve_token: ad.serve_token,
            option_index: idx,
            event_id: createEventId()
          }, function (response) {
            if (response && response.poll_results) {
              applyResults(response.poll_results, idx);
            }
          });
        }
      });

      optionBtns.push(btn);
      optionsList.appendChild(btn);
    });

    card.appendChild(optionsList);

    // Footer: vote count + CTA button
    var footer = document.createElement("div");
    footer.style.display = "flex";
    footer.style.alignItems = "center";
    footer.style.justifyContent = "space-between";
    footer.style.marginTop = "8px";
    footer.style.fontSize = "11px";
    footer.style.color = "#71717a";

    var footerStatus = document.createElement("span");
    footerStatus.textContent = (initialStats.total_votes || 0) + " votes";
    footer.appendChild(footerStatus);

    var ctaBtn = document.createElement("a");
    ctaBtn.href = ad.click_url;
    ctaBtn.target = "_blank";
    ctaBtn.rel = "noopener sponsored";
    ctaBtn.textContent = "Learn More →";
    ctaBtn.style.color = "#818cf8";
    ctaBtn.style.textDecoration = "none";
    ctaBtn.style.fontWeight = "600";
    ctaBtn.style.display = "none";
    footer.appendChild(ctaBtn);

    card.appendChild(footer);

    container.appendChild(card);
    if (ad.creative_id != null) container.dataset.creativeId = ad.creative_id;
    if (ad.campaign_id != null) container.dataset.campaignId = ad.campaign_id;

    return { link: sponsorLink, frame: card, ctaLink: ctaBtn };
  }

  function renderCreative(container, ad, socket, adUnitId) {
    if (!ad || !ad.asset_url || !ad.click_url) {
      console.error("[ad-loader] Received an invalid ad response.", ad);
      return null;
    }

    if (ad.format === "poll") {
      return renderPollCreative(container, ad, socket, adUnitId);
    }

    container.innerHTML = "";
    container.style.display = "";

    var creativeFrame = document.createElement("div");
    creativeFrame.style.position = "relative";
    creativeFrame.style.display = "inline-block";
    creativeFrame.style.maxWidth = "100%";
    creativeFrame.style.lineHeight = "0";

    var link = document.createElement("a");
    link.href = ad.click_url;
    link.target = "_blank";
    link.rel = "noopener sponsored";

    var media;
    if (ad.format === "video") {
      media = document.createElement("video");
      media.src = ad.asset_url;
      media.muted = true;          // required for autoplay
      media.autoplay = true;
      media.loop = true;
      media.playsInline = true;
      media.preload = "metadata";
      media.setAttribute("aria-label", ad.alt_text || "Advertisement");
    } else {
      media = document.createElement("img");
      media.src = ad.asset_url;
      media.alt = ad.alt_text || "Advertisement";
      media.loading = "lazy";
    }
    media.style.maxWidth = "100%";
    media.style.height = "auto";
    if (Number(ad.width) > 0) media.width = Number(ad.width);
    if (Number(ad.height) > 0) media.height = Number(ad.height);

    link.appendChild(media);
    creativeFrame.appendChild(link);
    container.appendChild(creativeFrame);
    if (ad.creative_id != null) container.dataset.creativeId = ad.creative_id;
    if (ad.campaign_id != null) container.dataset.campaignId = ad.campaign_id;
    return { link: link, frame: creativeFrame };
  }


  function createEventId() {
    if (window.crypto && window.crypto.randomUUID) return window.crypto.randomUUID();
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (char) {
      var random = Math.random() * 16 | 0;
      return (char === "x" ? random : (random & 3 | 8)).toString(16);
    });
  }

  function addReportControl(frame, socket, adUnitId, ad) {
    if (!ad.creative_id) return;

    var details = document.createElement("details");
    details.style.position = "absolute";
    details.style.top = "4px";
    details.style.right = "4px";
    details.style.zIndex = "2";
    details.style.fontSize = "12px";

    var summary = document.createElement("summary");
    summary.textContent = "⚑";
    summary.setAttribute("aria-label", "Report this ad");
    summary.title = "Report this ad";
    summary.style.cursor = "pointer";
    summary.style.listStyle = "none";
    summary.style.background = "rgba(0, 0, 0, 0.72)";
    summary.style.color = "#fff";
    summary.style.borderRadius = "3px";
    summary.style.padding = "4px 7px";
    summary.style.lineHeight = "1";
    details.appendChild(summary);

    var controls = document.createElement("div");
    controls.style.display = "flex";
    controls.style.gap = "6px";
    controls.style.alignItems = "center";
    controls.style.marginTop = "4px";
    controls.style.padding = "6px";
    controls.style.background = "rgba(0, 0, 0, 0.82)";
    controls.style.borderRadius = "4px";

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
        visitor_id: ad.visitor_id,
        serve_token: ad.serve_token,
        reason: reason.value
      }, function (response) {
        message.textContent = response && response.message
          ? response.message
          : "Could not submit the report. Please try again.";
        if (response && response.ok) {
          frame.innerHTML = "";
          frame.style.display = "flex";
          frame.style.alignItems = "center";
          frame.style.justifyContent = "center";
          frame.style.width = (Number(ad.width) > 0 ? Number(ad.width) : 300) + "px";
          frame.style.height = (Number(ad.height) > 0 ? Number(ad.height) : 250) + "px";
          frame.style.background = "#f3f4f6";
          frame.style.color = "#4b5563";
          frame.style.font = "14px sans-serif";
          frame.style.lineHeight = "normal";
          frame.textContent = "Reported";
        } else {
          submit.disabled = false;
        }
      });
    });

    controls.appendChild(reason);
    controls.appendChild(submit);
    controls.appendChild(message);
    details.appendChild(controls);
    frame.appendChild(details);
  }

  function setupViewabilityTracking(frame, socket, adUnitId, ad) {
    if (!ad.creative_id || !ad.serve_token || !ad.visitor_id) return;

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          // Ad entered viewport - send viewable_impression event
          socket.emit("viewable_impression", {
            ad_unit_id: adUnitId,
            creative_id: ad.creative_id,
            visitor_id: ad.visitor_id,
            serve_token: ad.serve_token,
            event_id: createEventId()
          });
          // Only fire once per ad
          observer.disconnect();
        }
      });
    }, {
      threshold: 0.5,
      rootMargin: "0px"
    });

    observer.observe(frame);
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
      if (!ad || !ad.serve_token || !ad.visitor_id) {
        console.error("[ad-loader] Ad response is missing its tracking token or visitor ID.");
        return;
      }
      var rendered = renderCreative(container, ad, socket, adUnitId);
      if (!rendered) return;

      function trackClick() {
        socket.emit("click", {
          ad_unit_id: adUnitId,
          creative_id: ad.creative_id,
          visitor_id: ad.visitor_id,
          serve_token: ad.serve_token,
          event_id: createEventId()
        });
      }

      if (rendered.link) rendered.link.addEventListener("click", trackClick);
      if (rendered.ctaLink) rendered.ctaLink.addEventListener("click", trackClick);
      socket.emit("impression", {
        ad_unit_id: adUnitId,
        creative_id: ad.creative_id,
        visitor_id: ad.visitor_id,
        serve_token: ad.serve_token,
        event_id: createEventId()
      });
      addReportControl(rendered.frame, socket, adUnitId, ad);
      setupViewabilityTracking(rendered.frame, socket, adUnitId, ad);
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
