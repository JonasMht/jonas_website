/* Boot: mark the document as JS-capable before first paint.
   Kept external (not inline) so the site needs no CSP hash — the header can stay
   a flat `script-src 'self'` and never drift out of date. Must stay blocking
   (no defer): the .js class gates the reveal animation, so adding it late would
   flash the content in and then hide it. */
document.documentElement.classList.add("js");
try {
    var savedTheme = localStorage.getItem("jm.theme");
    if (savedTheme === "light" || savedTheme === "dark") {
        document.documentElement.dataset.theme = savedTheme;
    }
} catch (e) {}
