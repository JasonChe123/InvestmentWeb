let theme = localStorage.getItem('theme');
if(theme === "dark") {
    setTheme(true);
}
else {
    setTheme(false);
}

function setTheme(isDark) {
    $('html').attr('data-bs-theme', isDark ? 'dark' : 'light');
    $('.theme-toggle').find('i').removeClass(isDark ? 'fa-sun' : 'fa-moon');
    $('.theme-toggle').find('i').addClass(isDark ? 'fa-moon' : 'fa-sun');
    $('.theme-toggle').find('b').text(isDark ? 'Dark' : 'Light');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
}