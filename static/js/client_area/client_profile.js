document.addEventListener('DOMContentLoaded', function() {
    // Handle profile picture selection and preview
    const profilePictureInput = document.getElementById('profile-picture-input');
    const profilePicture = document.getElementById('profile-picture');

    if (profilePictureInput && profilePicture) {
        profilePictureInput.addEventListener('change', function(e) {
            if (e.target.files && e.target.files[0]) {
                const reader = new FileReader();
                
                reader.onload = function(event) {
                    profilePicture.src = event.target.result;
                }
                
                reader.readAsDataURL(e.target.files[0]);
            }
        });
    }
});
