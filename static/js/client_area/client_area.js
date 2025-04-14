$(document).ready(function() {
    // Profile picture upload preview
    $('#profile-picture-input').change(function() {
        if (this.files && this.files[0]) {
            var reader = new FileReader();
            reader.onload = function(e) {
                $('#profile-picture').attr('src', e.target.result);
            }
            reader.readAsDataURL(this.files[0]);
            
            // Submit the form when file is selected
            $('#profile-picture-form').submit();
        }
    });
    
    // Handle form submission
    $('#profile-picture-form').on('submit', function(e) {
        e.preventDefault();
        var formData = new FormData(this);
        
        $.ajax({
            url: "{% url 'client_area:update_profile_picture' %}",
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function(response) {
                if(response.success) {
                    showToast('Profile picture updated successfully', 'success');
                } else {
                    showToast('Error updating profile picture', 'error');
                }
            },
            error: function() {
                showToast('Error updating profile picture', 'error');
            }
        });
    });
    
    function showToast(message, type) {
        // Create toast element
        var toast = $('<div>', {
            class: 'toast ' + type,
            text: message
        }).appendTo('body');
        
        // Show toast
        toast.fadeIn();
        
        // Hide after 3 seconds
        setTimeout(function() {
            toast.fadeOut(function() {
                $(this).remove();
            });
        }, 3000);
    }
});
