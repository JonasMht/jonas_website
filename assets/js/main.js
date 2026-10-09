(function () {
    "use strict";

    /* Keep the theme choice across pages; dark remains the site's default. */
    var themeButton = document.querySelector("[data-theme-toggle]");
    function syncTheme() {
        var light = document.documentElement.dataset.theme === "light";
        if (themeButton) {
            var label = light ? "Switch to dark mode" : "Switch to light mode";
            themeButton.setAttribute("aria-label", label);
            themeButton.setAttribute("title", label);
        }
        var themeMeta = document.querySelector('meta[name="theme-color"]');
        if (themeMeta) themeMeta.content = light ? "#F3F6FA" : "#0C0F14";
    }
    if (themeButton) {
        themeButton.addEventListener("click", function () {
            var theme = document.documentElement.dataset.theme === "light" ? "dark" : "light";
            document.documentElement.dataset.theme = theme;
            try {
                localStorage.setItem("jm.theme", theme);
            } catch (e) {}
            syncTheme();
        });
        syncTheme();
    }

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
    window.addEventListener(
        "scroll",
        function () {
            if (!tick) {
                tick = true;
                requestAnimationFrame(paint);
            }
        },
        { passive: true },
    );
    paint();

    /* First-party telemetry. An empty endpoint disables event collection. */
    var selfScript = document.currentScript || document.querySelector("script[data-telemetry]");
    var TEP = (selfScript && selfScript.dataset.telemetry) || "";
    var dnt = navigator.doNotTrack === "1" || window.doNotTrack === "1";
    var teleOff = false;
    var telemetryPersistent = true;
    var telemetryIdsCleared = true;
    var queue = [];
    var maxDepth = 0;
    var t0 = Date.now();
    var flushed = false;
    var deviceClass = /Android|iPhone|Mobile/.test(navigator.userAgent)
        ? "mobile"
        : /iPad|Tablet/.test(navigator.userAgent)
          ? "tablet"
          : "desktop";
    try {
        teleOff = localStorage.getItem("jm.telemetry") === "off";
    } catch (error) {
        telemetryPersistent = false;
    }

    function teleActive() {
        return Boolean(TEP) && !dnt && !teleOff;
    }

    function uuid() {
        try {
            if (crypto.randomUUID) return crypto.randomUUID();
        } catch (error) {}
        return "v-" + Date.now() + "-" + Math.random().toString(36).slice(2, 10);
    }

    function vid() {
        try {
            var v = localStorage.getItem("jm.visitor.v1");
            if (!v) {
                v = uuid();
                localStorage.setItem("jm.visitor.v1", v);
            }
            return v;
        } catch (error) {
            return null;
        }
    }

    function sid() {
        try {
            var s = JSON.parse(sessionStorage.getItem("jm.session.v1") || "null");
            if (
                !s ||
                typeof s.id !== "string" ||
                !Number.isFinite(s.t) ||
                Date.now() - s.t > 1800000
            ) {
                s = { id: uuid(), t: Date.now() };
            }
            s.t = Date.now();
            sessionStorage.setItem("jm.session.v1", JSON.stringify(s));
            return s.id;
        } catch (error) {
            return null;
        }
    }

    function push(event) {
        if (!teleActive()) return;
        event.v = vid();
        event.s = sid();
        event.b = deviceClass;
        event.r = document.referrer ? new URL(document.referrer).origin : "";
        queue.push(event);
        if (queue.length >= 8) flush();
    }

    function flush() {
        if (!queue.length || !teleActive()) return;
        var batch = JSON.stringify(queue);
        queue = [];
        var sent = false;
        try {
            sent = navigator.sendBeacon(
                TEP,
                new Blob([batch], { type: "text/plain;charset=UTF-8" }),
            );
        } catch (error) {
            /* Use fetch when sendBeacon is unavailable or refused. */
        }
        if (!sent)
            fetch(TEP, { method: "POST", body: batch, keepalive: true }).catch(function () {});
    }

    /* The console can query/change the preference without accessing the queue.
       Disabling drops pending events and IDs; enabling works without a reload. */
    document.addEventListener("jm:telemetry-request", function (event) {
        var enabled = event.detail && event.detail.enabled;
        if (typeof enabled === "boolean") {
            var wasActive = teleActive();
            teleOff = !enabled;
            try {
                if (enabled) localStorage.removeItem("jm.telemetry");
                else localStorage.setItem("jm.telemetry", "off");
                telemetryPersistent = true;
            } catch (error) {
                telemetryPersistent = false;
            }
            if (!enabled) {
                queue = [];
                telemetryIdsCleared = true;
                try {
                    localStorage.removeItem("jm.visitor.v1");
                } catch (error) {
                    telemetryIdsCleared = false;
                }
                try {
                    sessionStorage.removeItem("jm.session.v1");
                } catch (error) {
                    telemetryIdsCleared = false;
                }
            } else if (!wasActive && teleActive()) {
                t0 = Date.now();
                flushed = false;
                maxDepth = 0;
                push({ t: "pv", p: location.pathname });
            }
        }
        document.dispatchEvent(
            new CustomEvent("jm:telemetry-status", {
                detail: {
                    configured: Boolean(TEP),
                    active: teleActive(),
                    dnt: dnt,
                    optedOut: teleOff,
                    persistent: telemetryPersistent,
                    identifiersCleared: telemetryIdsCleared,
                },
            }),
        );
    });

    window.addEventListener("storage", function (event) {
        if (event.key !== "jm.telemetry" && event.key !== null) return;
        document.dispatchEvent(
            new CustomEvent("jm:telemetry-request", {
                detail: { enabled: event.key !== "jm.telemetry" || event.newValue !== "off" },
            }),
        );
    });

    if (TEP) {
        push({ t: "pv", p: location.pathname });
        document.addEventListener(
            "click",
            function (ev) {
                if (!teleActive() || ev.target.closest("#console, #console-toggle")) return;
                var dh = Math.max(1, document.documentElement.scrollHeight);
                push({
                    t: "clk",
                    p: location.pathname,
                    x: +(ev.clientX / window.innerWidth).toFixed(3),
                    y: +((ev.clientY + window.scrollY) / dh).toFixed(3),
                });
            },
            true,
        );
        document.addEventListener(
            "scroll",
            function () {
                if (!teleActive()) return;
                var h = document.documentElement;
                var d = Math.round(
                    ((h.scrollTop + h.clientHeight) / Math.max(1, h.scrollHeight)) * 100,
                );
                if (d > maxDepth) maxDepth = d;
            },
            { passive: true },
        );
        function onLeave() {
            if (flushed || !teleActive()) return;
            flushed = true;
            push({
                t: "dur",
                p: location.pathname,
                d: maxDepth,
                w: Math.round((Date.now() - t0) / 1000),
            });
            flush();
        }
        window.addEventListener("pagehide", onLeave);
        document.addEventListener("visibilitychange", function () {
            if (document.visibilityState === "hidden") onLeave();
        });
        setInterval(flush, 5000);
    }

    /* Content is ready on arrival; feedback belongs to the controls. */
    document.querySelectorAll(".reveal, .stagger").forEach(function (element) {
        element.classList.add("is-in");
    });

    /* hover prefetch — pages start loading before the click, navigation feels instant */
    var prefetched = {};
    document.addEventListener(
        "mouseover",
        function (ev) {
            var a = ev.target.closest && ev.target.closest('a[href^="/"]');
            if (!a || a.closest(".yt-facade")) return;
            var href = (a.getAttribute("href") || "").split("#")[0];
            if (
                !href ||
                prefetched[href] ||
                /\.(pdf|jpe?g|png|webp|svg|gif|ico|css|js|json|xml|txt)$/i.test(href)
            )
                return;
            prefetched[href] = 1;
            var l = document.createElement("link");
            l.rel = "prefetch";
            l.href = href;
            document.head.appendChild(l);
        },
        { passive: true },
    );

    /* YouTube thumbnails load as images; the player starts only on request. */
    function playFacade(f) {
        var ifr = document.createElement("iframe");
        ifr.src = "https://www.youtube-nocookie.com/embed/" + f.dataset.yt + "?autoplay=1";
        ifr.allow =
            "accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture; web-share; fullscreen";
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
        if (f && !f.classList.contains("is-live")) {
            ev.preventDefault();
            playFacade(f);
        }
    });

    /* The same Tabler symbols are used by static and generated controls. */
    var iconSprite = document.body.dataset.iconSprite;
    function copyIcon(name, className) {
        return (
            '<svg class="icon ' +
            className +
            '" viewBox="0 0 24 24" fill="none" ' +
            'stroke="currentColor" stroke-width="1.75" stroke-linecap="round" ' +
            'stroke-linejoin="round" aria-hidden="true" focusable="false"><use href="' +
            iconSprite +
            "#" +
            name +
            '"></use></svg>'
        );
    }
    var CLIP_SVG =
        copyIcon("copy", "copy-default") + copyIcon("check", "copy-success") + "<span>Copy</span>";

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
        if (sel) {
            var s = window.getSelection();
            if (s && s.rangeCount) s.removeAllRanges();
        }
    }
    function doCopy(text) {
        return new Promise(function (resolve) {
            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(text).then(
                    function () {
                        resolve(true);
                    },
                    function () {
                        resolve(fallbackCopy(text));
                    },
                );
            } else resolve(fallbackCopy(text));
        });
    }
    function fallbackCopy(text) {
        var previousFocus = document.activeElement;
        var ta = document.createElement("textarea");
        ta.value = text;
        ta.setAttribute("readonly", "");
        ta.style.position = "fixed";
        ta.style.top = "0";
        ta.style.left = "-9999px";
        document.body.appendChild(ta);
        clearSel();
        ta.focus();
        ta.setSelectionRange(0, ta.value.length);
        var ok = false;
        try {
            ok = document.execCommand("copy");
        } catch (e) {}
        clearSel();
        ta.blur();
        ta.remove();
        if (previousFocus && previousFocus.isConnected)
            previousFocus.focus({ preventScroll: true });
        return ok;
    }
    function showBadge(el, ev) {
        var old = document.querySelector(".copy-badge-wrap");
        if (old) old.remove();
        var x, y;
        if (ev && (ev.clientX || ev.clientY)) {
            x = ev.clientX;
            y = ev.clientY;
        } else {
            var r = el.getBoundingClientRect();
            x = r.left + r.width / 2;
            y = r.top;
        }
        var w = document.createElement("span");
        w.className = "copy-badge-wrap";
        w.setAttribute("aria-hidden", "true");
        w.style.cssText =
            "position:fixed;left:" +
            x +
            "px;top:" +
            y +
            "px;transform:translate(-50%,-130%);z-index:60;pointer-events:none;";
        var b = document.createElement("span");
        b.className = "copy-badge";
        b.textContent = "COPIED";
        w.appendChild(b);
        document.body.appendChild(w);
        setTimeout(function () {
            w.remove();
        }, 1500);
    }
    var liveRegion = null;
    function announce(msg) {
        if (!liveRegion) {
            liveRegion = document.createElement("div");
            liveRegion.setAttribute("aria-live", "polite");
            liveRegion.style.cssText =
                "position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);";
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
                if (!ok) {
                    btn.classList.add("is-error");
                    label.textContent = "Try again";
                    announce("Copy failed. Select the text and copy it manually.");
                    clearTimeout(t);
                    t = setTimeout(function () {
                        btn.classList.remove("is-error");
                        label.textContent = label0;
                    }, 2000);
                    return;
                }
                btn.classList.remove("is-error");
                btn.classList.add("is-done");
                label.textContent = "Copied";
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
    document
        .querySelectorAll(".article-content .highlight, .post .highlight")
        .forEach(function (hl) {
            var pre = hl.querySelector("pre");
            if (!pre) return;
            var btn = makeCopyBtn();
            hl.appendChild(btn);
            wireCopy(
                btn,
                function () {
                    return pre.innerText.replace(/\n+$/, "");
                },
                function (on) {
                    hl.classList.toggle("is-copied", on);
                },
            );
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
        if (ORCID.test(text) && a.tagName !== "A") {
            a.classList.add("copyable");
            a.setAttribute("role", "button");
            a.setAttribute("tabindex", "0");
            a.setAttribute("aria-label", "Copy ORCID iD " + value + " to clipboard");
            if (a.tagName !== "A") {
                a.addEventListener("keydown", function (ev) {
                    if (ev.key === "Enter" || ev.key === " ") {
                        ev.preventDefault();
                        a.click();
                    }
                });
            } else {
                a.addEventListener(
                    "click",
                    function (ev) {
                        ev.preventDefault();
                    },
                    true,
                );
            }
            a.addEventListener("click", function (ev) {
                doCopy(value).then(function (ok) {
                    if (ok) {
                        showBadge(a, ev);
                        announce("Copied to clipboard");
                    }
                });
            });
        } else {
            var chip = makeCopyBtn();
            chip.classList.add("inline");
            chip.setAttribute(
                "aria-label",
                "Copy " + (ORCID.test(value) ? "ORCID: " : "DOI: ") + value,
            );
            wireCopy(chip, function () {
                return value;
            });
            a.insertAdjacentElement("afterend", chip);
        }
    });

    /* One value drives pointer, touch, keyboard and accessible slider state. */
    var cmp = document.getElementById("cmp");
    if (cmp) {
        var top = cmp.querySelector(".s-top");
        var handle = cmp.querySelector(".s-handle");
        var pct = 50;
        var pointerId = null;

        function setPct(value) {
            pct = Math.max(0, Math.min(100, value));
            top.style.clipPath = "inset(0 " + (100 - pct) + "% 0 0)";
            handle.style.left = pct + "%";
            handle.setAttribute("aria-valuenow", String(Math.round(pct)));
            handle.setAttribute(
                "aria-valuetext",
                Math.round(pct) + "% wireframe, " + (100 - Math.round(pct)) + "% shaded",
            );
        }

        function moveSeam(event) {
            var rect = cmp.getBoundingClientRect();
            setPct((100 * (event.clientX - rect.left)) / rect.width);
        }

        cmp.addEventListener("pointerdown", function (event) {
            if (!event.isPrimary || (event.pointerType === "mouse" && event.button !== 0)) return;
            pointerId = event.pointerId;
            cmp.setPointerCapture(pointerId);
            handle.focus({ preventScroll: true });
            moveSeam(event);
        });
        cmp.addEventListener("pointermove", function (event) {
            if (event.pointerId === pointerId) moveSeam(event);
        });
        function endDrag() {
            pointerId = null;
        }
        cmp.addEventListener("pointerup", endDrag);
        cmp.addEventListener("pointercancel", endDrag);
        cmp.addEventListener("lostpointercapture", endDrag);
        handle.addEventListener("keydown", function (event) {
            var values = {
                ArrowLeft: pct - 2,
                ArrowDown: pct - 2,
                ArrowRight: pct + 2,
                ArrowUp: pct + 2,
                PageDown: pct - 10,
                PageUp: pct + 10,
                Home: 0,
                End: 100,
            };
            if (Object.prototype.hasOwnProperty.call(values, event.key)) {
                event.preventDefault();
                setPct(values[event.key]);
            }
        });
        setPct(pct);
    }
})();
