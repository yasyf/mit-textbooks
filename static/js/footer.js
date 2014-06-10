window.fbAsyncInit = function() {
  FB.init({
    appId      : '1497643403780485',
    xfbml      : true,
    version    : 'v2.0'
  });
};

(function(d, s, id){
   var js, fjs = d.getElementsByTagName(s)[0];
   if (d.getElementById(id)) {return;}
   js = d.createElement(s); js.id = id; js.async = true;
   js.src = "//connect.facebook.net/en_US/sdk.js";
   fjs.parentNode.insertBefore(js, fjs);
 }(document, 'script', 'facebook-jssdk'));

var trackOutboundLink = function(url, c, s) {
  ga('send', 'event', 'outbound', s.toLowerCase(), url, c*.04);
  window.open(url);
}

$('.popover_activate').popover();
if (window.matchMedia("only screen and (min-width : 769px)").matches) {
  var mit_textbooks_re = /((([A-Za-z]{2,3})|(([1][0-2,4-8]|[2][0-2,4]|[1-9])[AWFHLMawfhlm]?))\.([0-9]{2,4}[AJaj]?))/g;
  var client = new AlgoliaSearch('XBE4YTW1TS', '7a8a7ecc7cf2935949f179ba1567aef1');
  var index = client.initIndex('classes');
  var loading = false;
  var currentPreview = null;
  function load_preview (suggestion) {
    if(suggestion && suggestion.objectID != currentPreview) {
      currentPreview = suggestion.objectID;
      url = "/class/oid/_id?instant=true #body".replace('_id',currentPreview);
      $('#preview_body').load(url, function () {
        $('#body').fadeOut();
        $('#preview_body').fadeIn();
        $('#search_input').addClass('algolia');
      });
    }
  }
  $('#search_input').typeahead(
    {
      highlight: true,
      hint: true
    },
    {
      source: function (query, cb) {
        matches = query.match(mit_textbooks_re);
        params = {"advancedSyntax": true};
        if (query.indexOf(',') !== -1) {
          query = currentPreview;
        }
        else if(matches){
          // filters = "(class:{},master_subject_id:{})".replace(/\{\}/g,matches[0]);
          // params.facetFilters = filters;
          //query = "'" + query + "'";
          params.queryType = 'prefixNone';
          //params.minWordSizefor1Typo = 999;
        }
        cb2 = function (suggestions) {
          cb(suggestions);
          load_preview(suggestions[0]);
        }
        return index.ttAdapter(params)(query, cb2);
      },
      displayKey: 'class',
      templates: {
        suggestion: function (suggestion) {
          name = suggestion.short_name ? suggestion.short_name : suggestion.name;
          name = name.replace('&amp;','&').substring(0,29-suggestion.class.length);
          inner = suggestion.class + ' <small>' + name + '</small>';
          return '<p class="algolia">' + inner + '</p>';
        }
      }
  });
  $("#search_input").focus(function(e) { $(this).select(); });
  $("#search_input").mouseup(function(e) { e.preventDefault(); });
  $("#search_input").bind("typeahead:selected", function(e,s) {
    loading = true;
    $('#search_oid').val(s.objectID);
    $('#search').submit();
  });
  $("#search_input").bind("typeahead:cursorchanged", function(e,s) {
    load_preview(s);
  });
  $("#search_input").bind("typeahead:closed", function() {
    if(!loading) {
      $('#search_input').removeClass('algolia');
      $('#preview_body').fadeOut();
      $('#body').fadeIn();
    }
  });
}