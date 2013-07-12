$(document).ready(function(){
    $(document).find('.overlay-form-reload').prepOverlay({
        subtype: 'ajax',
        filter: common_content_filter,
        closeselector: '#form-buttons-cancel',
        formselector: '#form',
        noform: function(el) {return jQuery.plonepopups.noformerrorshow(el, 'reload');},
        config: {
            closeOnClick: false,
            closeOnEsc: false
        }
    });
    $(document).find('.overlay-form-redirect').prepOverlay({
        subtype: 'ajax',
        filter: common_content_filter,
        closeselector: '#form-buttons-cancel',
        formselector: '#form',
        redirect: $.plonepopups.redirectbasehref,
        noform: function(el) {return jQuery.plonepopups.noformerrorshow(el, 'redirect');},
        config: {
            closeOnClick: false,
            closeOnEsc: false
        }
    });
    $(document).find('.overlay-comment-form').prepOverlay({
        subtype: 'ajax',
        filter: common_content_filter,
        closeselector: '#form-buttons-cancel',
        formselector: '#commenting form',
        redirect: $.plonepopups.redirectbasehref,
        noform: function(el) {return jQuery.plonepopups.noformerrorshow(el, 'redirect');},
        config: {
            closeOnClick: true,
            closeOnEsc: true
        }
    });
});
