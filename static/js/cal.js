var clientId = '822985175941-3bpj4hdfidarnvoomqclji9pff15ehif.apps.googleusercontent.com';

var apiKey = 'AIzaSyA8suueSVCtKCEYnnMn0f70QGkzsO3JSnA';

var scopes = ['https://www.googleapis.com/auth/calendar'];

function unescapeHtml(unsafe) {
  return unsafe
      .replace(/&amp;/g, "and");
}

function handleClientLoad() {
  gapi.client.setApiKey(apiKey);
}

function handleAuthResult(authResult) {
  if (authResult && !authResult.error) {
    makeApiCall();
  }
}

function handleAuthClick() {
  gapi.auth.authorize({client_id: clientId, scope: scopes, immediate: false}, handleAuthResult);
  return false;
}

function makeApiCall() {
  gapi.client.load('calendar', 'v3', function() {
    var request = gapi.client.calendar.calendarList.list();
    request.execute(function(resp) {
      $.each(resp.items, function(i, obj) {  
        if (obj.primary){
          $('#calendar_choices')
           .append($("<option></option>")
           .attr("value", obj.id)
           .attr("selected", "selected")
           .text(obj.summary)); 
         } 
         else {
          $('#calendar_choices')
           .append($("<option></option>")
           .attr("value",obj.id)
           .text(obj.summary)); 
         }
        
      });
      $("#gcal_modal").modal();
    });
  });
}

function handleGoClick (calendarId) {
  if($("#gcal_btn").text() == "Submit") {
      $("#gcal_message").text("Adding " + unescapeHtml(resources[0].summary));
      makeApiCall2(calendarId);
  }
  else{
     $("#gcal_modal").modal("hide");
     $("#gcal_btn").text("Submit");
  }
}
