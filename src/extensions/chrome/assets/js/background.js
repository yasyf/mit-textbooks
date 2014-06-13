function loadJSON(path, success, error)
{
    var xhr = new XMLHttpRequest();
    xhr.onreadystatechange = function()
    {
        if (xhr.readyState === 4) {
            if (xhr.status === 200) {
                if (success)
                    success(JSON.parse(xhr.responseText));
            } else {
                if (error)
                    error(xhr);
            }
        }
    };
    xhr.open("GET", path, true);
    xhr.send();
}

function navigate(url) {
  chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
    chrome.tabs.update(tabs[0].id, {url: url});
  });
}

chrome.omnibox.setDefaultSuggestion({'description': '<dim>Search MIT Textbooks</dim>'});

chrome.omnibox.onInputChanged.addListener(function (text, suggest) {
    loadJSON('http://textbooksearch.mit.edu/suggest/'+text, function (data) {
    	suggestions = [];
    	for (var i = data.suggestions.length - 1; i >= 0; i--) {
    		suggestions.push({'content': data.suggestions[i].c, 'description': data.suggestions[i].n.replace(text,'<match>'+text+'</match>') + ' on MIT Textbooks'});
    	};
    	suggest(suggestions);
    });
});
chrome.omnibox.onInputEntered.addListener(function (text) {
    navigate('http://textbooksearch.mit.edu/go/'+text);
});