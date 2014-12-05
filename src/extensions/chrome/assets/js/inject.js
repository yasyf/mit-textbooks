(function(){
	var mit_textbooks_re = /(http:\/\/.*)?((([A-Za-z]{2,3})|(([1][0-2,4-8]|[2][0-2,4]|[1-9])[AWFHLMawfhlm]?))\.(([sS]?[0-9]{2,4}[AJaj]?)|([uU][aA][TtRr])))/g;
	var mit_textbooks_re_search = /([\s,\(]|^)((([A-Za-z]{2,3})|(([1][0-2,4-8]|[2][0-2,4]|[1-9])[AWFHLMawfhlm]?))\.(([sS]?[0-9]{2,4}[AJaj]?)|([uU][aA][TtRr])))(([,\s\?\!\)](?!([%]|GB)))|([\.](?!([0-9])))|$)/g;
	var mit_textbooks_replace = "<a data-tbclass='$2' href='http://textbooksearch.mit.edu/go/$2' style='text-decoration:none;' target='_blank'>$2</a>";
	var mit_textbooks_inject_re = /http[s]?:\/\/(www\.)?amazon\.[\w]{2,3}/;
	var mit_textbooks_inject_replace_re = /tag=[\w\-]+/;
	var mit_textbooks_current_html;

	function checkNode(node) {
		var excludes = ["script", "a", "input", "button", "textarea", "font", "h1", "h2", "h3", "header", "markdown"];
		var bad_roles = ["textbox", "alert"];
		if (node.attr('data-tb') === 'replaced') {
			return false;
		}
		if ($.inArray(node.prop("tagName").toLowerCase(), excludes) !== -1) {
			return false;
		}
		if ($.inArray(node.attr('role'), bad_roles) !== -1) {
			return false;
		}
		if (node.css('cursor') === 'pointer') {
			return false;
		}
		if (node.attr('id') === 'header') {
			return false;
		}
		if (node.hasClass('markdown')) {
			return false;
		}
		if (node.attr('draggable') === "true") {
			return false;
		}
		return true;
	}

	function getStars(rating) {
		output = "";
		for (var i = 0; i < Math.floor(rating); i++) {
			output += "<img src='" + chrome.extension.getURL('/assets/img/star_ffe600_16.png') + "'>";
		}
		if (parseFloat(rating.toString().split('.').slice(-1)[0]) > 0.5) {
			output += "<img style='position: relative; left: -3px;' src='" + chrome.extension.getURL('/assets/img/star-half_ffe600_16.png') + "'>";
		}
		if (output) {
			output += '<br>';
		}
		return output;
	}

	function shouldInject (node) {
		if (node.tagName && node.tagName.toLowerCase() === "a" && node.getAttribute('href') && node.getAttribute('href').toLowerCase().indexOf('amazon') !== -1) {
			return true;
		}
		return false;
	}

	function injectLink(node) {
		if (node.attr('data-tb-injected') === 'true') {
			return
		}
		href = node.attr('href').toLowerCase();
		matches = href.match(mit_textbooks_inject_re);
		if (matches) {
			if (href.indexOf('tag=') !== -1){
				href = href.replace(mit_textbooks_inject_replace_re, "tag=mit-tb-20");
			}
			else if (href.indexOf('?') !== -1) {
				href += '&tag=mit-tb-20';
			}
			else {
				href += '?tag=mit-tb-20';
			}
			node.attr('href', href);
			node.attr('data-tb-injected', 'true');
		}
	}

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
				var skip = false;
				$.each($(node).parents(), function(index, value) {
					if(checkNode($(value)) === false){
						skip = true;
						return false;
					}
				});
				if (skip) {
					continue;
				}
				span = document.createElement('span');
				span.setAttribute('data-tb', 'replaced');
				span.innerHTML = node.nodeValue.replace(mit_textbooks_re, function(match, url, klass) {
					if (url) {
						return match;
					} else {
						return mit_textbooks_replace.replace(/\$2/g, klass);
					}
				});
				node.parentNode.replaceChild(span, node);
			}
		}

		var walker2 = document.createTreeWalker(
		  document.body,
		  NodeFilter.SHOW_ELEMENT,
		  function(node) {
		    if(shouldInject(node)) {
		      return NodeFilter.FILTER_ACCEPT;
		    } else {
		      return NodeFilter.FILTER_SKIP;
		    }
		  },
		  false);

		var nodes2 = [];

		while(walker2.nextNode()) {
		  nodes2.push(walker2.currentNode);
		}

		for(var i = 0; node=nodes2[i] ; i++) {
			injectLink($(node));
		}

		if ($('[data-tbclass]').size() < 50){
			$('[data-tbclass]').each(function (index) {
				var elt = $(this);
				var c = elt.attr('data-tbclass');
				elt.removeAttr('data-tbclass');
				$.getJSON('https://mit-textbooks.herokuapp.com/popover/'+c, function(data) {
					if (data.class_info) {
						elt.text(data.class_info.c);
						elt.qtip({
							content: {
								title: data.class_info.n,
								text: getStars(data.class_info.r) + data.class_info.d
							},
							position: {
								my: 'top center',
								at: 'bottom center',
								target: 'event',
								viewport: $(window)
							},
							style: {
								classes: 'qtip-bootstrap'
							},
							show: {
								effect: function(offset) {
									$(this).slideDown(250);
								},
								delay: 200,
								solo: true,
							},
							hide: {
								effect: function(offset) {
									$(this).slideUp(250);
								},
								delay: 200,
								fixed: true
							}
						});
					}
					else {
						elt.contents().unwrap();
					}
				});
			});
		}
		mit_textbooks_current_html = document.documentElement.innerHTML;
	}

	if (document.getElementById('mit-tb-home')) {
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
})()
