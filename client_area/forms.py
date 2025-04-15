from django import forms
from .models import Profile
from django.core.exceptions import ValidationError
import os

class ProfileForm(forms.ModelForm):
    
    class Meta:
        model = Profile
        fields = ['profile_picture']

    def clean_profile_picture(self):
        picture = self.cleaned_data.get('profile_picture', False)
        if picture:
            # Validate file size (max 2MB)
            if picture.size > 2 * 1024 * 1024:
                raise ValidationError("Image file too large ( > 2MB )")
            # Validate file extension
            ext = os.path.splitext(picture.name)[1].lower()
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
            if ext not in valid_extensions:
                raise ValidationError("Unsupported file extension. Allowed: jpg, jpeg, png, gif")
        return picture
