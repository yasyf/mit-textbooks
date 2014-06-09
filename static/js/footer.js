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
!function(a){var b="embedly-platform",c="script";if(!a.getElementById(b)){var d=a.createElement(c);d.id=b,d.src=("https:"===document.location.protocol?"https":"http")+"://cdn.embedly.com/widgets/platform.js";d.async=1;var e=document.getElementsByTagName(c)[0];e.parentNode.insertBefore(d,e)}}(document);
$('.popover_activate').popover();
if (window.matchMedia("only screen and (min-width : 769px)").matches) {
  var mit_textbooks_re = /((([A-Za-z]{2,3})|(([1][0-2,4-8]|[2][0-2,4]|[1-9])[AWFHLMawfhlm]?))\.([0-9]{2,4}[AJaj]?))/g;
  var client = new AlgoliaSearch('XBE4YTW1TS', '7a8a7ecc7cf2935949f179ba1567aef1');
  var index = client.initIndex('classes');
  var loading = false;
  $('#search_input').typeahead(
    {
      highlight: true,
      hint: true
    },
    {
      source: function (query, cb) {
        matches = query.match(mit_textbooks_re);
        params = {"advancedSyntax": true};
        if(matches){
          // filters = "(class:{},master_subject_id:{})".replace(/\{\}/g,matches[0]);
          // params.facetFilters = filters;
          query = "'" + query + "'";
          params.queryType = 'prefixNone';
          params.minWordSizefor1Typo = 999;
        } 
        return index.ttAdapter(params)(query, cb);
      },
      displayKey: 'class',
      templates: {
        suggestion: function (suggestion) {
          name = suggestion.short_name ? suggestion.short_name : suggestion.name;
          inner = suggestion.class + ' <small>' + name.substring(0,21-suggestion.class.length) + '</small>';
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
    url = "/class/oid/_id?instant=true #body".replace('_id',s.objectID);
    $('#preview_body').load(url, function () {
      $('#body').fadeOut();
      $('#preview_body').fadeIn();
    });
  });
  $("#search_input").bind("typeahead:closed", function() {
    if(!loading) {
      $('#preview_body').fadeOut();
      $('#body').fadeIn();
    }
  });
}