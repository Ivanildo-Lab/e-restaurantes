from django import forms


class AutoCompleteWidget(forms.Select):
    def __init__(self, api_url, placeholder='Buscar...', attrs=None):
        self.api_url = api_url
        self.placeholder = placeholder
        default_attrs = {'class': 'autocomplete-input', 'autocomplete': 'off'}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)

    def build_attrs(self, base_attrs, extra_attrs=None):
        attrs = super().build_attrs(base_attrs, extra_attrs)
        attrs['data-api-url'] = self.api_url
        attrs['placeholder'] = self.placeholder
        return attrs
