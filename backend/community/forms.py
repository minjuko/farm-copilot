from django import forms
from .models import Post, Comment

MAX_POST_IMAGE_SIZE = 5 * 1024 * 1024

class PostForm(forms.ModelForm):
    POST_TYPE_CHOICES = [
        ('buy', 'Buy'),
        ('sell', 'Sell'),
        ('exchange', 'Exchange')
    ]
    post_type = forms.ChoiceField(choices=POST_TYPE_CHOICES, required=True, widget=forms.Select)

    class Meta:
        model = Post
        fields = ['title', 'content', 'post_type', 'image']

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image and image.size > MAX_POST_IMAGE_SIZE:
            raise forms.ValidationError('Image size must not exceed 5 MB.')
        return image

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
