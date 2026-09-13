from django import forms


class RichTextEditorWidget(forms.Textarea):
    """
    Textarea rendered into an advanced TinyMCE editor in the custom admin.
    The init script (static/js/richtext_init.js) finds any textarea marked
    with data-editor="tinymce" and replaces it with the editor on load.
    """

    def __init__(self, attrs=None):
        default_attrs = {
            'data-editor': 'tinymce',
            'rows': 30,
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)