$(document).ready(function () {
    // Toggle theme
    const themeToggle = $('#theme-toggle');
    const icon = themeToggle.find('i');
    const themeText = themeToggle.find('label')
    const htmlElement = $('html');

    let theme = localStorage.getItem('theme');
    setTheme(theme === 'light');

    function setTheme(isDark) {
        htmlElement.attr('data-bs-theme', isDark ? 'dark' : 'light');
        icon.removeClass(isDark ? 'fa-sun' : 'fa-moon');
        icon.addClass(isDark ? 'fa-moon' : 'fa-sun');
        themeText.text(isDark ? 'Dark' : 'Light');
    }

    themeToggle.click(function () {
        const isDark = htmlElement.attr('data-bs-theme') === 'dark';
        setTheme(!isDark);
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
    });
});