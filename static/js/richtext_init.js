/* Advanced WYSIWYG editor for the custom Django admin.
   Initializes TinyMCE 7 (loaded from jsDelivr CDN) on every
   textarea marked with data-editor="tinymce". */
(function () {
    'use strict';

    function getCookie(name) {
        var v = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
        return v ? v.pop() : '';
    }

    function initEditor(el) {
        if (window.tinymce === undefined) {
            return;
        }
        tinymce.init({
            target: el,
            height: 520,
            menubar: false,
            branding: false,
            license_key: 'gpl',
            toolbar_mode: 'wrap',
            convert_urls: false,
            extended_valid_elements: '*[*]',
            valid_children: '+body[style],+body[script],+body[link]',
            plugins: 'advlist autolink lists link image charmap anchor searchreplace ' +
                     'visualblocks code fullscreen insertdatetime table media help wordcount ' +
                     'preview autoresize',
            toolbar: [
                'undo redo | blocks fontfamily fontsize',
                'bold italic underline strikethrough | forecolor backcolor',
                'alignleft aligncenter alignright alignjustify | outdent indent',
                'bullist numlist | link image media table | removeformat preview code fullscreen'
            ].join(' '),
            content_style: 'body { font-family: "Segoe UI", Tahoma, sans-serif, "SolaimanLipi"; font-size: 15px; line-height: 1.8; }',
            automatic_uploads: true,
            file_picker_types: 'image',
            images_upload_handler: function (blobInfo, success, failure) {
                var fd = new FormData();
                fd.append('file', blobInfo.blob(), blobInfo.filename());
                fetch('/admin/upload-image/', {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: { 'X-CSRFToken': getCookie('csrftoken') },
                    body: fd
                })
                .then(function (res) {
                    if (!res.ok) {
                        throw new Error('Upload failed: HTTP ' + res.status);
                    }
                    return res.json();
                })
                .then(function (data) {
                    if (data && data.location) {
                        success(data.location);
                    } else {
                        failure(data && data.error ? data.error : 'Upload failed');
                    }
                })
                .catch(function (err) {
                    failure(err.message || 'Upload failed');
                });
            }
        });
    }

    function ready(fn) {
        if (document.readyState !== 'loading') {
            fn();
        } else {
            document.addEventListener('DOMContentLoaded', fn);
        }
    }

    ready(function () {
        var els = document.querySelectorAll('textarea[data-editor="tinymce"]');
        for (var i = 0; i < els.length; i++) {
            initEditor(els[i]);
        }
    });
})();