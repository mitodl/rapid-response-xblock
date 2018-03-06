(function($, _) {
  'use strict';
  function RapidResponseAsideView(runtime, element) {
    var toggleStatusUrl = runtime.handlerUrl(element, 'toggle_block_open_status');
    var $element = $(element);

    var rapidTopLevelSel = '.rapid-response-block';
    var rapidBlockContentSel = '#rapid-response-content';
    var toggleTemplate = _.template($(element).find("#rapid-response-toggle-tmpl").text());

    function render(state) {
      // Render template
      var $rapidBlockContent = $element.find(rapidBlockContentSel);
      $rapidBlockContent.html(toggleTemplate(state));

      $rapidBlockContent.find('.problem-status-toggle').click(function(e) {
        $.get(toggleStatusUrl).then(
          function(state) {
            render(state);
          }
        ).fail(
          function () {
            console.log("toggle data FAILED [" + toggleStatusUrl + "]");
          }
        );
      });
    }

    $(function($) { // onLoad
      var block = $element.find(rapidTopLevelSel);
      var isOpen = block.attr('data-open') === 'True';
      var isStaff = block.attr('data-staff') === 'True';
      render({
        is_open: isOpen,
        is_staff: isStaff
      });
    });
  }

  function initializeRapidResponseAside(runtime, element) {
    return new RapidResponseAsideView(runtime, element);
  }

  window.RapidResponseAsideInit = initializeRapidResponseAside;
}($, _));
