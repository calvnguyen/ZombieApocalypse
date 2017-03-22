# handling form inputs
from django import forms

from models import Game


class GameForm(forms.ModelForm):
    class Meta:
        exclude = ['date']
        model = Game

    def clean_infected_population(self):
        """Validate infected population"""
        data = self.cleaned_data['infected_population']
        if data <= 0.0 or data >= 100.0:
            raise forms.ValidationError("Infected population must be greater than zero and less than 100%")
        return data
