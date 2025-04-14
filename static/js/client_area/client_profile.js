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

    // Handle form submission
    const editProfileForm = document.getElementById('edit-profile-form');
    if (editProfileForm) {
        editProfileForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            
            fetch(window.location.href, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                }
            })
            .then(response => {
                if (response.redirected) {
                    window.location.href = response.url;
                }
            })
            .catch(error => {
                console.error('Error:', error);
            });
        });
    }
});
