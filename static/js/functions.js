function resetCookies () {
    $.removeCookie("id_email");
    $.removeCookie("id_name");
}
$(document).ready(function() {
    $( "#search_input" ).focus(function() {
        if(window.innerWidth >= 769){
            $( "#gobtn" ).fadeTo( 400, 1, "swing" );
        }
      
    });
    $( "#search_input" ).focusout(function() {
        if(window.innerWidth >= 769){
            $( "#gobtn" ).fadeTo( 400, 0, "swing" );
        }
    });
});
function check_sell(id) {
    var passing = true;
    $('#error'+id).html('');
    $('#condition_parent'+id).addClass('has-success');
    if ($('#email'+id).val().substring($('#email'+id).val().indexOf('@') + 1).toLowerCase() === 'mit.edu') {
        $('#email_parent'+id).addClass('has-success');
        $('#email_parent'+id).removeClass('has-error');
    } else {
        passing = false;
        append_error(id, 'An MIT email is required.');
        $('#email_parent'+id).addClass('has-error');
        $('#email_parent'+id).removeClass('has-success');
    } if ($.isNumeric($('#price'+id).val())) {
        $('#price_parent'+id).addClass('has-success');
        $('#price_parent'+id).removeClass('has-error');
    } else {
        passing = false;
        append_error(id, 'The asking price must be numeric.');
        $('#price_parent'+id).addClass('has-error');
        $('#price_parent'+id).removeClass('has-success');
    } if ($.isNumeric($('#price'+id).val()) && parseInt($('#price'+id).val()) < parseInt($('#retail'+id).text())) {
        $('#price_parent'+id).addClass('has-success');
        $('#price_parent'+id).removeClass('has-error');
    } else if($.isNumeric($('#price'+id).val())) {
        passing = false;
        append_error(id, 'The asking price must be below retail value.');
        $('#price_parent'+id).addClass('has-error');
        $('#price_parent'+id).removeClass('has-success');
    } if (!$('#location'+id).val()) {
        passing = false;
        append_error(id, 'You must give a valid location.');
        $('#location_parent'+id).addClass('has-error');
        $('#location_parent'+id).removeClass('has-success');
    } else {
        $('#location_parent'+id).addClass('has-success');
        $('#location_parent'+id).removeClass('has-error');
    } if (passing == true) {
        $('#submit'+id).addClass('disabled');
        $('#error'+id).html('');
        $('#form'+id).submit();
    };
}
function append_error(id, ttext) {
    if ($('#error'+id).html() == '') {
        $('#error'+id).html(ttext);
    } else {
        $('#error'+id).html($('#error'+id).html() + '<br>' + ttext)
    }
}

function animateTo (selector) {
    $('html, body').animate({
        scrollTop: $(selector).offset().top - 75
    }, 500);
}