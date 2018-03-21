(function($, _) {
  'use strict';

  function RapidResponseAsideStudioView(runtime, element) {
    var toggleEnabledUrl = runtime.handlerUrl(element, 'toggle_block_enabled');
    var $element = $(element);

    var rapidTopLevelSel = '.rapid-response-block';
    var rapidBlockContentSel = '.rapid-response-content';
    var enabledCheckboxSel = '.rapid-enabled-toggle';
    var toggleTemplate = _.template($(element).find("#rapid-response-toggle-tmpl").text());

    function render(state) {
      // Render template
      var $rapidBlockContent = $element.find(rapidBlockContentSel);
      $rapidBlockContent.html(toggleTemplate(state));

      $rapidBlockContent.find(enabledCheckboxSel).click(function() {
        $.post(toggleEnabledUrl).then(
          function(state) {
            render(state);
          }
        );
      });
    }

    $(function() { // onLoad
      var block = $element.find(rapidTopLevelSel);
      var isEnabled = block.attr('data-enabled') === 'True';
      render({
        is_enabled: isEnabled
      });
    });
  }

  function initializeRapidResponseAside(runtime, element) {
    return new RapidResponseAsideStudioView(runtime, element);
  }

  window.RapidResponseAsideStudioInit = initializeRapidResponseAside;
}($, _));
