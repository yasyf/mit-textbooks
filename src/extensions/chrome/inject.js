var mit_textbooks_re = /([\w]{1,3}\.[0-9]{2,3}[\w]{0,1})/g;
var mit_textbooks_replace = "<a href='http://textbooksearch.mit.edu/go/$1' target='_blank'>$1</a>";
var mit_textbooks_current_html;
function walkDom() {
	if (mit_textbooks_current_html == document.documentElement.innerHTML) {
		return;
	}
	var walker = document.createTreeWalker(
	  document.body,
	  NodeFilter.SHOW_TEXT,
	  function(node) {
	    var matches = node.textContent.match(mit_textbooks_re);
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
		if (node.parentNode){
			node.parentNode.innerHTML = node.parentNode.innerHTML.replace(mit_textbooks_re, mit_textbooks_replace);
		}
	}
	mit_textbooks_current_html = document.documentElement.innerHTML;
}

walkDom();

window.setInterval(walkDom, 10000);