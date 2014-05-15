var mit_textbooks_re = /((([A-Za-z]{2,3})|([1-9][0-9]?[AWFHLMawfhlm]?))\.([0-9]{2,4}[AJaj]?))/g;
var mit_textbooks_re_search = /(\s|^)((([A-Za-z]{2,3})|([1-9][0-9]?[AWFHLMawfhlm]?))\.([0-9]{2,4}[AJaj]?))(([\s\?\.\!](?!([%]|GB)))|$)/g;
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
			excludes = ["a", "input", "button", "textarea"];
			if (_.contains(excludes, node.parentNode.tagName.toLowerCase()) || window.getComputedStyle(node.parentNode).cursor === 'pointer'){
				continue;
			}
			if (node.parentNode.parentNode && node.parentNode.parentNode.getAttribute('role') === 'textbox'){
				continue;
			}
			span = document.createElement('span');
			span.setAttribute('data-x', node.parentNode.tagName.toLowerCase());
			span.innerHTML = node.nodeValue.replace(mit_textbooks_re, mit_textbooks_replace);
			node.parentNode.replaceChild(span, node);
		}
	}
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
