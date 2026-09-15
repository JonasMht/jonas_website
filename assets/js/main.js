(function () {
    "use strict";

    /* Theme toggle */
    var root = document.documentElement;
    var toggle = document.querySelector(".theme-toggle");
    if (toggle) {
        toggle.addEventListener("click", function () {
            var next = root.dataset.scheme === "dark" ? "light" : "dark";
            root.dataset.scheme = next;
            try { localStorage.setItem("scheme", next); } catch (e) {}
        });
    }

    /* Mobile nav */
    var navToggle = document.querySelector(".nav-toggle");
    var navMenu = document.getElementById("nav-menu");
    if (navToggle && navMenu) {
        navToggle.addEventListener("click", function () {
            var open = navMenu.classList.toggle("is-open");
            navToggle.setAttribute("aria-expanded", String(open));
        });
    }

    /* Reveal on scroll */
    var reveal = function () {
        var els = document.querySelectorAll(".reveal");
        if (!("IntersectionObserver" in window)) {
            els.forEach(function (el) { el.classList.add("is-in"); });
            return;
        }
        var io = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add("is-in");
                    io.unobserve(entry.target);
                }
            });
        }, { threshold: 0.08 });
        els.forEach(function (el) { io.observe(el); });
    };
    if (document.readyState !== "loading") reveal();
    else document.addEventListener("DOMContentLoaded", reveal);
})();
