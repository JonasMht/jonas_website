(function () {
    "use strict";

    /* ignition blink — ≤300ms, once per session, skipped under reduced-motion */
    var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!reduce) document.body.classList.add("rm-ok");
    var ign = document.querySelector(".ignition");
    if (ign && !reduce) {
        var seen = null;
        try { seen = sessionStorage.getItem("jm.ignited"); } catch (e) {}
        if (seen) { ign.classList.add("is-done"); }
        else {
            try { sessionStorage.setItem("jm.ignited", "1"); } catch (e) {}
            setTimeout(function () {
                ign.classList.add("is-done");
                setTimeout(function () { ign.remove(); }, 400);
            }, 240);
        }
    } else if (ign) { ign.remove(); }

    /* power-on reveals — progressive enhancement, visible by default without JS */
    var els = document.querySelectorAll(".reveal");
    if (reduce || !("IntersectionObserver" in window)) {
        els.forEach(function (el) { el.classList.add("is-in"); });
    } else {
        var io = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add("is-in");
                    io.unobserve(entry.target);
                }
            });
        }, { threshold: 0, rootMargin: "0px 0px 360px 0px" });
        els.forEach(function (el) { io.observe(el); });
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
        if (ev.key !== "Enter") return;
        var raw = input.value.trim();
        input.value = "";
        if (!raw) return;
        line("› " + raw, "p");
        var parts = raw.split(/\s+/);
        var cmd = parts[0].toLowerCase();
        if (cmd === "help") {
            line("help — this list");
            line("session — your visit, as local telemetry");
            line("goto <path> — jump to a station path (e.g. goto /pro/)");
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
        } else if (cmd === "clear") {
            try { localStorage.removeItem(KEY); } catch (e) {}
            body.textContent = "";
            line("▸ local profile wiped. nothing was ever sent anywhere.");
        } else {
            line("unknown command — type `help`");
        }
    });
})();
