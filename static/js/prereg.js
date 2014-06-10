function createFrame(src) {
	$('<iframe />').attr('id', 'registerFrame').attr('src', src).attr('height','0').attr('width','0').appendTo('body');
	$('#registerFrame').load(function() { 
  $('#registerFrame').remove();
    next();
  });
}
function next() {
	if (classes.length === 0) {
		window.open('http://student.mit.edu/catalog/viewcookie.cgi');
	}
	else {
		c = classes.pop();
		createFrame('http://student.mit.edu/catalog/editcookie.cgi?add='+c);
	}
}
function preRegister(){
	createFrame('http://student.mit.edu/catalog/editcookie.cgi?reset=all');
}