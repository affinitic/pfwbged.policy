$(document).ready(function(){
    $(document).find('.pfwb-overlay-form-reload').prepOverlay({
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
});
