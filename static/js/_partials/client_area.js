$(document).ready(function () {
    console.log("client area js loaded.");

    // Sidebar toggle functionality
    const sidebar = document.getElementById('sidebar');
    const toggleBtn = document.getElementById('sidebar-toggle-btn');

    toggleBtn.addEventListener('click', () => {
        sidebar.classList.toggle('collapsed');
        if (sidebar.classList.contains('collapsed')) {
            toggleBtn.textContent = '>'; // Change arrow direction
        } else {
            toggleBtn.textContent = '<'; // Change arrow direction
        }
    });

    /*
    console.log("client area js loaded");
    // Theme toggling
    const themeToggle = $('.theme-toggle');
    const icon = themeToggle.find('i');
    const themeText = themeToggle.find('b')
    const htmlElement = $('html');
    const sidebarToggleBtn = $('#sidebar-toggle-btn');
    const sidebar = $('#sidebar');

    function setTheme(isDark) {
        htmlElement.attr('data-bs-theme', isDark ? 'dark' : 'light');
        icon.removeClass(isDark ? 'fa-sun' : 'fa-moon');
        icon.addClass(isDark ? 'fa-moon' : 'fa-sun');
        themeText.text(isDark ? 'Dark' : 'Light');
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
    }

    // ToggleTheme button
    themeToggle.click(function () {
        const isDark = htmlElement.attr('data-bs-theme') === 'dark';
        setTheme(!isDark);
    });

    // // Toogle sidebar
    // function toggleSidebar() {
    //     if (sidebar.width() > 60) {
    //         sidebar.width("60px");
    //         sidebarToggleBtn.text(">");
    //     } else {
    //         sidebar.width("300px");
    //         sidebarToggleBtn.text("<");
    //     }
    // }

    // Sidebar toggling
    sidebar.css({ "transition": "width 0.5s ease" });
    sidebar.find("a").css({
        "white-space": 'nowrap',
    });
    sidebarToggleBtn.click(function () {
        toggleSidebar();
    });
    sidebar.find("button").click(function () {
        if (!(sidebar.width() > 60)) {
            toggleSidebar();
        }
    });
    console.log("client area js loaded finished");
    */
});
