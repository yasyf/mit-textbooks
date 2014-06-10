 $('body').scrollspy({ target: '#nav-parent', offset: 75 });

var $root = $('html, body');
$('.sidebar-link').click(function() {
    var href = $.attr(this, 'href');
    $root.animate({
        scrollTop: $(href).offset().top - 75
    }, 500, function () {
        window.location.hash = href;
    });
    return false;
});