(function($, _) {
  'use strict';

  // time between polls of responses API
  var POLLING_MILLIS = 3000;

  function RapidResponseAsideView(runtime, element) {
    var toggleStatusUrl = runtime.handlerUrl(element, 'toggle_block_open_status');
    var responsesUrl = runtime.handlerUrl(element, 'responses');
    var $element = $(element);

    var rapidTopLevelSel = '.rapid-response-block';
    var rapidBlockContentSel = '#rapid-response-content';
    var toggleTemplate = _.template($(element).find("#rapid-response-toggle-tmpl").text());

    // default values
    var state = {
      is_open: false,
      is_staff: false,
      responses: []
    };

    function render() {
      // Render template
      var $rapidBlockContent = $element.find(rapidBlockContentSel);
      $rapidBlockContent.html(toggleTemplate(state));

      $rapidBlockContent.find('.problem-status-toggle').click(function(e) {
        $.get(toggleStatusUrl).then(
          function(newState) {
            state = Object.assign({}, state, newState);
            render();

            pollForResponses();
          }
        ).fail(
          function () {
            console.log("toggle data FAILED [" + toggleStatusUrl + "]");
          }
        );
      });
    }

    function pollForResponses() {
      $.get(responsesUrl).then(function(newState) {
        state = Object.assign({}, state, newState);
        render();
        if (state.is_open) {
          setTimeout(pollForResponses, POLLING_MILLIS);
        }
      }).fail(function () {
        // TODO: try again?
        console.error("Error retrieving response data");
      });
    }

    $(function($) { // onLoad
      var block = $element.find(rapidTopLevelSel);
      var isOpen = block.attr('data-open') === 'True';
      var isStaff = block.attr('data-staff') === 'True';
      state.is_open = isOpen;
      state.is_staff = isStaff;
      render();

      if (isStaff) {
        pollForResponses();
      }
    });
  }

  function initializeRapidResponseAside(runtime, element) {
    return new RapidResponseAsideView(runtime, element);
  }

  window.RapidResponseAsideInit = initializeRapidResponseAside;
}($, _));
