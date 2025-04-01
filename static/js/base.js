// Dark Mode Toggle
const darkModeToggle = document.getElementById('dark-mode-toggle');

darkModeToggle.addEventListener('click', () => {
    document.body.classList.toggle('dark-mode');
    if (document.body.classList.contains('dark-mode')) {
        darkModeToggle.textContent = 'Light';
        localStorage.setItem('theme', 'dark');
    } else {
        darkModeToggle.textContent = 'Dark';
        localStorage.setItem('theme', 'light');
    }
});

// Detect current theme
function isDarkTheme() {
    return localStorage.getItem('theme') === 'dark';
}

// Set theme in line with current theme
const isDark = isDarkTheme();
if (isDark && !document.body.classList.contains('dark-mode')) {
    document.body.classList.toggle('dark-mode');
} else {
    if (!isDark && document.body.classList.contains('dark-mode')) {
        document.body.classList.toggle('dark-mode');
    }
}