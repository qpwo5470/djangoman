from django.forms import ModelForm
from .models import Lazypixels


class LazypixelForm(ModelForm):
    class Meta:
        model = Lazypixels
        fields = ['image']
