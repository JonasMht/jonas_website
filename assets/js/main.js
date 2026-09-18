(function () {
    "use strict";

    /* scroll progress rail */
    var bar = document.createElement("div");
    bar.id = "progress";
    document.body.appendChild(bar);
    var tick = false;
    function paint() {
        var h = document.documentElement;
        var p = h.scrollTop / Math.max(1, h.scrollHeight - h.clientHeight);
        bar.style.transform = "scaleX(" + p + ")";
        tick = false;
    }
    window.addEventListener("scroll", function () {
        if (!tick) { tick = true; requestAnimationFrame(paint); }
    }, { passive: true });
    paint();

    /* ===== station telemetry — self-hosted, first-party, disclosed in /legal ===== */
    var TEP = window.TELEMETRY_ENDPOINT || "";
    var dnt = navigator.doNotTrack === "1" || window.doNotTrack === "1";
    var teleOff = null;
    try { teleOff = localStorage.getItem("jm.telemetry") === "off"; } catch (e) {}
    function teleActive() { return TEP && !dnt && !teleOff; }
    function uuid() {
        try { return crypto.randomUUID ? crypto.randomUUID() : "v-" + Date.now() + "-" + Math.random().toString(36).slice(2, 10); }
        catch (e) { return "v-" + Date.now(); }
    }
    function vid() {
        try {
            var v = localStorage.getItem("jm.visitor.v1");
            if (!v) { v = uuid(); localStorage.setItem("jm.visitor.v1", v); }
            return v;
        } catch (e) { return null; }
    }
    function sid() {
        try {
            var s = JSON.parse(sessionStorage.getItem("jm.session.v1") || "null");
            if (!s || Date.now() - s.t > 1800000) { s = { id: uuid(), t: Date.now() }; }
            s.t = Date.now();
            sessionStorage.setItem("jm.session.v1", JSON.stringify(s));
            return s.id;
        } catch (e) { return null; }
    }
    if (teleActive()) {
        var queue = [], maxDepth = 0, t0 = Date.now(), flushed = false;
        var BR = (function () { var a = navigator.userAgent; return /Android|iPhone|Mobile/.test(a) ? "mobile" : /iPad|Tablet/.test(a) ? "tablet" : "desktop"; })();
        function push(ev) {
            ev.v = vid(); ev.s = sid(); ev.b = BR; ev.r = document.referrer ? new URL(document.referrer).origin : "";
            queue.push(ev);
            if (queue.length >= 8) flush();
        }
        function flush() {
            if (!queue.length || !teleActive()) return;
            var batch = JSON.stringify(queue); queue = [];
            try { navigator.sendBeacon(TEP, new Blob([batch], { type: "text/plain;charset=UTF-8" })); }
            catch (e) { try { fetch(TEP, { method: "POST", body: batch, keepalive: true }); } catch (e2) {} }
        }
        push({ t: "pv", p: location.pathname });
        document.addEventListener("click", function (ev) {
            if (!teleActive()) return;
            var dh = Math.max(1, document.documentElement.scrollHeight);
            push({ t: "clk", p: location.pathname, x: +(ev.clientX / window.innerWidth).toFixed(3),
                y: +((ev.clientY + window.scrollY) / dh).toFixed(3) });
        }, true);
        document.addEventListener("scroll", function () {
            var h = document.documentElement;
            var d = Math.round(((h.scrollTop + h.clientHeight) / Math.max(1, h.scrollHeight)) * 100);
            if (d > maxDepth) maxDepth = d;
        }, { passive: true });
        function onLeave() {
            if (flushed || !teleActive()) return; flushed = true;
            push({ t: "dur", p: location.pathname, d: maxDepth, w: Math.round((Date.now() - t0) / 1000) });
            flush();
        }
        window.addEventListener("pagehide", onLeave);
        document.addEventListener("visibilitychange", function () { if (document.visibilityState === "hidden") onLeave(); });
        setInterval(flush, 5000);
    }

    /* ignition blink — ≤300ms, once per session, skipped under reduced-motion */
    var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!reduce) document.body.classList.add("rm-ok");
    var ign = document.querySelector(".ignition");
    if (ign && !reduce) {
        var seen = null;
        try { seen = sessionStorage.getItem("jm.ignited"); } catch (e) {}
        if (seen) { ign.remove(); }
        else {
            try { sessionStorage.setItem("jm.ignited", "1"); } catch (e) {}
            setTimeout(function () {
                ign.classList.add("is-done");
                setTimeout(function () { ign.remove(); }, 400);
            }, 240);
        }
    } else if (ign) { ign.remove(); }

    /* power-on reveals — progressive enhancement, visible by default without JS.
       back/forward navigations: everything is already in place, zero motion. */
    var navType = "";
    try { navType = (performance.getEntriesByType("navigation")[0] || {}).type || ""; } catch (e) {}
    var backFwd = navType === "back_forward";
    var els = document.querySelectorAll(".reveal");
    if (reduce || backFwd || !("IntersectionObserver" in window)) {
        els.forEach(function (el) { el.classList.add("is-in"); });
        if (backFwd) document.querySelectorAll(".stagger").forEach(function (g) { g.classList.add("is-in"); });
    } else {
        var io = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add("is-in");
                    entry.target.querySelectorAll(".stagger").forEach(function (g) {
                        if (g.classList.contains("is-in")) return;
                        g.classList.add("is-in");
                        var kids = g.children;
                        for (var i = 0; i < kids.length; i++) kids[i].style.transitionDelay = (i * 60) + "ms";
                        setTimeout(function () {
                            for (var i = 0; i < kids.length; i++) kids[i].style.transitionDelay = "";
                        }, 900);
                    });
                    io.unobserve(entry.target);
                }
            });
        }, { threshold: 0, rootMargin: "0px 0px 360px 0px" });
        els.forEach(function (el) { io.observe(el); });
    }

    /* hover prefetch — pages start loading before the click, navigation feels instant */
    var prefetched = {};
    document.addEventListener("mouseover", function (ev) {
        var a = ev.target.closest && ev.target.closest('a[href^="/"]');
        if (!a || a.closest(".yt-facade")) return;
        var href = (a.getAttribute("href") || "").split("#")[0];
        if (!href || prefetched[href] || /\.(pdf|jpe?g|png|webp|svg|gif|ico|css|js|json|xml|txt)$/i.test(href)) return;
        prefetched[href] = 1;
        var l = document.createElement("link");
        l.rel = "prefetch";
        l.href = href;
        document.head.appendChild(l);
    }, { passive: true });

    /* station pulse — public aggregates only, refreshes every 30s */
    var pulseV = document.getElementById("pulse-v7");
    if (pulseV && TEP) {
        var pulseBase = TEP.replace(/\/e$/, "");
        var pulseTick = function () {
            fetch(pulseBase + "/api/pulse").then(function (r) { return r.json(); }).then(function (d) {
                pulseV.textContent = String(d.v7);
                var sub = document.getElementById("pulse-sub");
                if (!sub) return;
                var up = Math.max(0, d.now - d.since);
                var days = Math.floor(up / 86400), hrs = Math.floor((up % 86400) / 3600);
                sub.textContent = "visitors · 7d · up " + (days ? days + "d " : "") + hrs + "h";
            }).catch(function () {
                var sub = document.getElementById("pulse-sub");
                if (sub) sub.textContent = "pulse offline";
            });
        };
        pulseTick();
        setInterval(pulseTick, 30000);
    }

    /* press-and-hold lock-on — touch devices get the focus wedges while holding.
       touch events (not pointer events): browsers fire pointercancel when their
       own link gestures take over, which killed the hold on tablets. */
    var hold = { t: null, card: null, x: 0, y: 0, fired: false };
    function holdEnd() {
        clearTimeout(hold.t);
        if (hold.card) hold.card.classList.remove("hold");
        hold.card = null; hold.t = null;
    }
    document.addEventListener("touchstart", function (ev) {
        var card = ev.target.closest && ev.target.closest(".card");
        if (!card || !ev.touches.length) return;
        holdEnd();
        hold.card = card; hold.x = ev.touches[0].clientX; hold.y = ev.touches[0].clientY; hold.fired = false;
        hold.t = setTimeout(function () {
            hold.card.classList.add("hold");
            hold.fired = true;
            if (navigator.vibrate) { try { navigator.vibrate(12); } catch (e) {} }
        }, 380);
    }, { passive: true });
    document.addEventListener("touchmove", function (ev) {
        if (!hold.t || !ev.touches.length) return;
        if (Math.abs(ev.touches[0].clientX - hold.x) > 12 || Math.abs(ev.touches[0].clientY - hold.y) > 12) holdEnd();
    }, { passive: true });
    ["touchend", "touchcancel"].forEach(function (t) {
        document.addEventListener(t, holdEnd, { passive: true });
    });
    document.addEventListener("contextmenu", function (ev) {
        if (hold.fired && ev.target.closest && ev.target.closest(".card")) ev.preventDefault();
    });
    document.addEventListener("click", function (ev) {
        if (hold.fired && ev.target.closest && ev.target.closest(".card")) {
            hold.fired = false;
            ev.preventDefault();
            ev.stopPropagation();
        }
    }, true);

    /* youtube facades — nothing third-party loads until the user presses play */
    function playFacade(f) {
        var ifr = document.createElement("iframe");
        ifr.src = "https://www.youtube-nocookie.com/embed/" + f.dataset.yt + "?autoplay=1";
        ifr.allow = "accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture; web-share; fullscreen";
        ifr.title = f.getAttribute("aria-label") || "YouTube video";
        ifr.setAttribute("allowfullscreen", "");
        f.textContent = "";
        f.appendChild(ifr);
        f.classList.add("is-live");
        f.removeAttribute("role");
        f.removeAttribute("tabindex");
    }
    document.addEventListener("click", function (ev) {
        var f = ev.target.closest && ev.target.closest(".yt-facade");
        if (f && !f.classList.contains("is-live")) playFacade(f);
    });
    document.addEventListener("keydown", function (ev) {
        if (ev.key !== "Enter" && ev.key !== " ") return;
        var f = ev.target.closest && ev.target.closest(".yt-facade");
        if (f && !f.classList.contains("is-live")) { ev.preventDefault(); playFacade(f); }
    });

    /* copy system — one interaction grammar everywhere:
       clipboard icon → check draws inside it → spring pop → settles back */
    var CLIP_SVG = '<svg viewBox="0 0 16 16" aria-hidden="true">' +
        '<rect x="4" y="3.9" width="8" height="10.2" rx="1.3" fill="none" stroke="currentColor" stroke-width="1.4"/>' +
        '<path d="M6.1 3.9V3.1a1.2 1.2 0 0 1 1.2-1.2h1.4a1.2 1.2 0 0 1 1.2 1.2v.8" fill="none" stroke="currentColor" stroke-width="1.4"/>' +
        '<path class="ck" d="M6.1 9 7.8 10.6 10.7 7" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg><span>COPY</span>';

    function makeCopyBtn() {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "copy-btn";
        btn.setAttribute("aria-label", "Copy to clipboard");
        btn.innerHTML = CLIP_SVG;
        return btn;
    }
    function clearSel() {
        var sel = window.getSelection;
        if (sel) { var s = window.getSelection(); if (s && s.rangeCount) s.removeAllRanges(); }
    }
    function doCopy(text) {
        return new Promise(function (resolve) {
            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(text).then(function () { resolve(true); }, function () { resolve(fallbackCopy(text)); });
            } else resolve(fallbackCopy(text));
        });
    }
    function fallbackCopy(text) {
        var ta = document.createElement("textarea");
        ta.value = text;
        ta.setAttribute("readonly", "");
        ta.style.position = "fixed"; ta.style.top = "0"; ta.style.left = "-9999px";
        document.body.appendChild(ta);
        clearSel();
        ta.focus();
        ta.setSelectionRange(0, ta.value.length);
        var ok = false;
        try { ok = document.execCommand("copy"); } catch (e) {}
        clearSel();
        ta.blur(); ta.remove();
        return ok;
    }
    function showBadge(el) {
        var old = el.querySelector(".copy-badge");
        if (old) old.remove();
        var b = document.createElement("span");
        b.className = "copy-badge";
        b.textContent = "COPIED";
        b.setAttribute("aria-hidden", "true");
        el.appendChild(b);
        setTimeout(function () { b.remove(); }, 1500);
    }
    var liveRegion = null;
    function announce(msg) {
        if (!liveRegion) {
            liveRegion = document.createElement("div");
            liveRegion.setAttribute("aria-live", "polite");
            liveRegion.style.cssText = "position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);";
            document.body.appendChild(liveRegion);
        }
        liveRegion.textContent = msg;
    }
    function wireCopy(btn, getText, after) {
        var label = btn.querySelector("span");
        var label0 = label.textContent;
        var t = null;
        btn.addEventListener("click", function () {
            clearSel();
            doCopy(getText()).then(function (ok) {
                if (!ok) return;
                btn.classList.add("is-done");
                label.textContent = "COPIED";
                if (after) after(true);
                announce("Copied to clipboard");
                clearTimeout(t);
                t = setTimeout(function () {
                    btn.classList.remove("is-done");
                    label.textContent = label0;
                    if (after) after(false);
                }, 1600);
            });
        });
        return btn;
    }

    /* code blocks */
    document.querySelectorAll(".article-content .highlight, .post .highlight").forEach(function (hl) {
        var pre = hl.querySelector("pre");
        if (!pre) return;
        var btn = makeCopyBtn();
        hl.appendChild(btn);
        wireCopy(btn, function () { return pre.innerText.replace(/\n+$/, ""); },
            function (on) { hl.classList.toggle("is-copied", on); });
    });

    /* copyable identifiers — ORCID text and links become click-to-copy;
       DOI links keep navigation and gain an inline copy chip */
    var ORCID = /^\d{4}-\d{4}-\d{4}-[\dXx]{4}$/;
    document.querySelectorAll("main a, main .mono-id-num").forEach(function (a) {
        if (a.closest(".highlight") || a.querySelector("img")) return;
        var text = (a.textContent || "").trim();
        var href = a.getAttribute("href") || "";
        var value = null;
        if (ORCID.test(text)) value = text;
        else if (href.indexOf("https://doi.org/") === 0) value = href.slice(16);
        else if (href.indexOf("http://doi.org/") === 0) value = href.slice(15);
        if (!value) return;
        if (ORCID.test(text)) {
            a.classList.add("copyable");
            a.setAttribute("role", "button");
            a.setAttribute("tabindex", "0");
            a.setAttribute("aria-label", "Copy ORCID iD " + value + " to clipboard");
            if (a.tagName !== "A") {
                a.addEventListener("keydown", function (ev) {
                    if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); a.click(); }
                });
            } else {
                a.addEventListener("click", function (ev) { ev.preventDefault(); }, true);
            }
            a.addEventListener("click", function () {
                doCopy(value).then(function (ok) {
                    if (ok) { showBadge(a); announce("Copied to clipboard"); }
                });
            });
        } else {
            var chip = makeCopyBtn();
            chip.classList.add("inline");
            chip.setAttribute("aria-label", "Copy DOI: " + value);
            wireCopy(chip, function () { return value; });
            a.insertAdjacentElement("afterend", chip);
        }
    });

    /* lab comparison slider */
    var cmp = document.getElementById("cmp");
    if (cmp) {
        var top = cmp.querySelector(".s-top"), handle = cmp.querySelector(".s-handle");
        var setPct = function (pct) {
            pct = Math.max(0, Math.min(100, pct));
            top.style.clipPath = "inset(0 " + (100 - pct) + "% 0 0)";
            handle.style.left = pct + "%";
        };
        var dragging = false;
        var move = function (ev) {
            if (!dragging) return;
            var r = cmp.getBoundingClientRect();
            setPct(((ev.clientX - r.left) / r.width) * 100);
        };
        cmp.addEventListener("pointerdown", function (ev) { dragging = true; move(ev); });
        window.addEventListener("pointermove", move);
        window.addEventListener("pointerup", function () { dragging = false; });
        var pct = 50;
        var apply = function () { setPct(pct); handle.setAttribute("aria-valuenow", Math.round(pct)); };
        handle.addEventListener("keydown", function (ev) {
            if (ev.key === "ArrowLeft" || ev.key === "ArrowRight") {
                ev.preventDefault();
                pct = Math.max(0, Math.min(100, pct + (ev.key === "ArrowRight" ? 4 : -4)));
                apply();
            }
        });
    }

    /* station console — opt-in, local only, nothing tracked */
    var box = document.getElementById("console");
    if (!box) return;
    var body = box.querySelector("#console-body");
    var input = box.querySelector("#console-input");
    var KEY = "jm.console.v1";

    function store() {
        var d = null;
        try { d = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) {}
        return d && typeof d === "object" ? d : {};
    }
    function logVisited() {
        try {
            var d = store();
            d.pages = d.pages || [];
            if (d.pages.indexOf(document.title) === -1) d.pages.push(document.title);
            d.last = new Date().toISOString();
            localStorage.setItem(KEY, JSON.stringify(d));
        } catch (e) {}
    }
    function line(text, cls) {
        var el = document.createElement("div");
        if (cls) el.className = cls;
        el.textContent = text;
        body.appendChild(el);
        body.scrollTop = body.scrollHeight;
    }
    var hist = [], hIdx = -1, sIdx = null;
    var COMMANDS = ["help", "session", "goto", "find", "telemetry", "clear"];
    function ensureIndex() {
        if (sIdx) return Promise.resolve(sIdx);
        return fetch("/searchindex.json").then(function (r) { return r.json(); }).then(function (d) {
            sIdx = d; return sIdx;
        }).catch(function () { return []; });
    }
    function complete() {
        var v = input.value;
        var parts = v.split(/\s+/);
        if (parts.length <= 1 && !/:\s*$/.test(v)) {
            var hits = COMMANDS.filter(function (c) { return c.indexOf(parts[0].toLowerCase()) === 0; });
            if (hits.length === 1) input.value = hits[0] + " ";
            else if (hits.length > 1) { line("▸ " + hits.join("  "), "p"); }
            return;
        }
        if (parts[0].toLowerCase() === "goto" && parts.length >= 2) {
            var frag = parts[parts.length - 1].toLowerCase();
            ensureIndex().then(function (idx) {
                var paths = idx.map(function (p) { return p.u; })
                    .filter(function (u) { return u.toLowerCase().indexOf(frag) === 0; });
                if (paths.length === 1) input.value = "goto " + paths[0];
                else if (paths.length > 1) paths.slice(0, 6).forEach(function (p) { line("▸ " + p, "p"); });
            });
        }
    }
    function sessionLine() {
        var d = store();
        var pages = (d.pages || []).length;
        line("▸ this visit: " + document.title, "hi");
        line("▸ profile: " + pages + " page" + (pages === 1 ? "" : "s") + " in local memory" + (d.last ? " · last seen " + d.last.slice(0, 10) : ""));
    }
    function openConsole() {
        box.hidden = false;
        box.classList.add("is-open");
        if (!body.dataset.init) {
            body.dataset.init = "1";
            line("STATION CONSOLE — local telemetry, honest theatre", "hi");
            line("type `help` for commands · `~` or ESC closes");
            logVisited();
            sessionLine();
        }
        setTimeout(function () { input.focus(); }, 30);
    }
    function closeConsole() {
        box.classList.remove("is-open");
        box.hidden = true;
    }
    document.addEventListener("keydown", function (ev) {
        var tag = (ev.target.tagName || "").toLowerCase();
        var typing = tag === "input" || tag === "textarea" || ev.target.isContentEditable;
        if ((ev.key === "~" || ev.key === "`") && !typing && !box.classList.contains("is-open")) {
            ev.preventDefault();
            openConsole();
        } else if (ev.key === "Escape" && box.classList.contains("is-open")) {
            closeConsole();
        }
    });
    input.addEventListener("keydown", function (ev) {
        if (ev.key === "ArrowUp" || ev.key === "ArrowDown") {
            if (!hist.length) return;
            ev.preventDefault();
            if (ev.key === "ArrowUp") { if (hIdx === -1) hIdx = hist.length; hIdx = Math.max(0, hIdx - 1); }
            else { hIdx = Math.min(hist.length, hIdx + 1); if (hIdx === hist.length) { input.value = ""; return; } }
            input.value = hist[hIdx] || "";
            return;
        }
        if (ev.key === "Tab") {
            ev.preventDefault();
            complete();
            return;
        }
        if (ev.key !== "Enter") return;
        var raw = input.value.trim();
        input.value = "";
        if (!raw) return;
        hist.push(raw); hIdx = -1;
        line("› " + raw, "p");
        var parts = raw.split(/\s+/);
        var cmd = parts[0].toLowerCase();
        if (cmd === "help") {
            line("help — this list");
            line("telemetry on|off — opt out of / back into station telemetry (see /legal)");
            line("session — your visit, as local telemetry");
            line("goto <path> — jump to a station path (e.g. goto /pro/)");
            line("find <words> — search the station (titles, tags, descriptions)");
            line("clear — wipe the local profile");
        } else if (cmd === "session") {
            sessionLine();
        } else if (cmd === "goto") {
            var path = parts[1] || "";
            if (!path) { line("goto needs a path — try: goto /pro/"); return; }
            if (!/^\//.test(path)) path = "/" + path;
            if (!/\/$/.test(path)) path += "/";
            line("▸ navigating to " + path + " …");
            setTimeout(function () { window.location.href = path; }, 250);
        } else if (cmd === "find") {
            var q = parts.slice(1).join(" ").toLowerCase();
            if (!q) { line("find needs words — e.g. find ablation"); return; }
            fetch("/searchindex.json").then(function (r) { return r.json(); }).then(function (idx) {
                var hits = idx.filter(function (p) {
                    return ((p.t + " " + (p.d || "") + " " + (p.g || []).join(" ")).toLowerCase().indexOf(q) !== -1);
                }).slice(0, 8);
                if (!hits.length) { line("no module matches: " + q); return; }
                hits.forEach(function (h) { line("▸ " + h.t + " → " + h.u); });
            }).catch(function () { line("search index unavailable"); });
        } else if (cmd === "telemetry") {
            var mode = (parts[1] || "").toLowerCase();
            if (mode === "off") {
                try { localStorage.setItem("jm.telemetry", "off"); localStorage.removeItem("jm.visitor.v1"); } catch (e) {}
                teleOff = true;
                line("▸ telemetry disabled — local profile wiped. nothing more leaves your browser.");
            } else if (mode === "on") {
                try { localStorage.removeItem("jm.telemetry"); } catch (e) {}
                teleOff = false;
                line("▸ telemetry re-enabled — see /legal for exactly what is stored.");
            } else { line("telemetry on — or — telemetry off"); }
        } else if (cmd === "clear") {
            try { localStorage.removeItem(KEY); } catch (e) {}
            body.textContent = "";
            line("▸ local profile wiped. nothing was ever sent anywhere.");
        } else {
            line("unknown command — type `help`");
        }
    });
})();
