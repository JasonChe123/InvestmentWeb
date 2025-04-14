$(document).ready(function () {
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
    const htmlElement = $('html');
    const sidebarToggleBtn = $('#sidebar-toggle-btn');
    const sidebar = $('#sidebar');

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
    */
});
