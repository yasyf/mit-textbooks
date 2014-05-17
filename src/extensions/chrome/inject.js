var mit_textbooks_re = /((([A-Za-z]{2,3})|(([1-2][0-9]|[1-9])[AWFHLMawfhlm]?))\.([0-9]{2,4}[AJaj]?))/g;
var mit_textbooks_re_search = /(\s|^)((([A-Za-z]{2,3})|(([1-2][0-9]|[1-9])[AWFHLMawfhlm]?))\.([0-9]{2,4}[AJaj]?))(([\s\?\.\!](?!([%]|GB)))|$)/g;
var mit_textbooks_replace = "<a data-tb='replaced' href='http://textbooksearch.mit.edu/go/$1' target='_blank'>$1</a>";
var mit_textbooks_current_html;
function walkDom() {
	if (mit_textbooks_current_html == document.documentElement.innerHTML) {
		return;
	}
	var walker = document.createTreeWalker(
	  document.body,
	  NodeFilter.SHOW_TEXT,
	  function(node) {
	    var matches = node.textContent.match(mit_textbooks_re_search);
	    if(matches) { 
	      return NodeFilter.FILTER_ACCEPT;
	    } else {
	      return NodeFilter.FILTER_SKIP;
	    }
	  },
	  false);

	var nodes = [];

	while(walker.nextNode()) {
	  nodes.push(walker.currentNode);
	}

	for(var i = 0; node=nodes[i] ; i++) {
		if (node.parentNode) {
			if (node.parentNode.getAttribute('data-tb') === 'replaced'){
				continue;
			}
			var excludes = ["script", "a", "input", "button", "textarea", "font"];
			var bad_roles = ["textbox", "alert"];
			var skip = false;
			$.each($(node).parents(), function(index, value) {
				if($.inArray(value.tagName.toLowerCase(), excludes) != -1 || $.inArray(value.getAttribute('role'), bad_roles) != -1 || $(value).css('cursor') === 'pointer'){
					skip = true;
					return false;
				}
			});
			if (skip) {
				continue;
			}
			span = document.createElement('span');
			span.setAttribute('data-tbclass', node.nodeValue.match(mit_textbooks_re)[0]);
			span.innerHTML = node.nodeValue.replace(mit_textbooks_re, mit_textbooks_replace);
			node.parentNode.replaceChild(span, node);
		}
	}

	$('[data-tbclass]').each(function (index) {
		var elt = $(this);
		var c = elt.attr('data-tbclass');
		elt.removeAttr('data-tbclass');
		$.getJSON('https://mit-textbooks.herokuapp.com/popover/'+c, function(data) {
			if (data.class_info) {
				elt.qtip({
					content: {
						title: data.class_info.n,
						text: data.class_info.d
					},
					position: {
						my: 'top center',
						at: 'bottom center',
						target: 'event'
					},
					style: { 
						classes: 'qtip-bootstrap'
					},
					show: {
						effect: function(offset) {
							$(this).slideDown();
						}
					},
					hide: {
						effect: function(offset) {
							$(this).slideUp();
						}
					}
				});

			}
		});
	});
	mit_textbooks_current_html = document.documentElement.innerHTML;
}

if (document.domain === "textbooksearch.mit.edu") {
	installP = document.getElementById('mit-tb-cr-ext');
	if (installP) {
		installP.style.display = 'none';
	}
} else {
	walkDom();
	window.setTimeout(walkDom, 1000);
	window.setTimeout(walkDom, 3000);
	window.setInterval(walkDom, 5000);
}
