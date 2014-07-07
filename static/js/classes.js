$(document).ready(function() {
  $('body').scrollspy({ target: '#nav-parent', offset: 100 });
  var timeout;
  $('#nav-parent').on('activate.bs.scrollspy', function () {
    clearTimeout(timeout);
    timeout = setTimeout(function(){
      $('#sidebar').animate({
        scrollTop: $('#sidebar').scrollTop() + $('li.active').position().top - 10
      }, 200);
      $('.list-group-item-danger').removeClass('list-group-item-danger');
      var id = $('li.active').children().first().attr('href');
      $(id).next().addClass('list-group-item-danger');
    }, 100);
    
  });

  var $root = $('html, body');
  $('.sidebar-link').click(function() {
      var href = $.attr(this, 'href');
      $root.animate({
          scrollTop: $(href).offset().top - 100
      }, 500, function () {
          window.location.hash = href;
      });
      return false;
  });
});
