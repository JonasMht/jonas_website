/* Restore theme before first paint and expose enhanced controls.
   This tiny external script keeps script-src 'self' and avoids a theme flash. */
document.documentElement.classList.add("js");
try {
    var savedTheme = localStorage.getItem("jm.theme");
    if (savedTheme === "light" || savedTheme === "dark") {
        document.documentElement.dataset.theme = savedTheme;
    }
} catch (e) {}
