(function($, _) {
  'use strict';

  // time between polls of responses API
  var POLLING_MILLIS = 3000;

  function RapidResponseAsideView(runtime, element) {
    var toggleStatusUrl = runtime.handlerUrl(element, 'toggle_block_open_status');
    var responsesUrl = runtime.handlerUrl(element, 'responses');
    var $element = $(element);

    var rapidTopLevelSel = '.rapid-response-block';
    var rapidBlockContentSel = '.rapid-response-content';
    var rapidBlockResultsSel = '.rapid-response-results';
    var toggleTemplate = _.template($(element).find("#rapid-response-toggle-tmpl").text());

    // default values
    var state = {
      is_open: false,
      is_staff: false,
      responses: []
    };

    /**
     * Render template
     */
    function render() {
      var $rapidBlockContent = $element.find(rapidBlockContentSel);
      $rapidBlockContent.html(toggleTemplate(state));
      renderD3(state);

      $rapidBlockContent.find('.problem-status-toggle').click(function(e) {
        $.get(toggleStatusUrl).then(
          function(newState) {
            state = Object.assign({}, state, newState);
            render();

            if (state.is_open) {
              pollForResponses();
            }
          }
        ).fail(
          function () {
            console.log("toggle data FAILED [" + toggleStatusUrl + "]");
          }
        );
      });
    }

    // Chart D3 element
    var chart;

    // This is a list of answer ids updated after each D3 update to keep track of the insertion order.
    var colorDomain;

    // TODO: These values are guesses, maybe we want to calculate based on browser width/height? Not sure
    var ChartSettings = {
      width: 1000,
      height: 500,
      top: 100,
      left: 80,
      bottom: 200,
      right: 80,
      messageLeft: 150,
      messageBottom: 100,
      noDataMessage: "No data available",
      numYAxisTicks: 6
    };

    /**
     * Initialize grade histogram elements.
     */
    function initD3() {
      var svg = d3.select(element).select(rapidBlockResultsSel).append("svg");

      svg.attr("width", ChartSettings.width + ChartSettings.left + ChartSettings.right);
      svg.attr("height", ChartSettings.height + ChartSettings.top + ChartSettings.bottom);
      // The g element has a little bit of padding so the x and y axes can surround it
      chart = svg.append("g");
      chart.attr("transform", "translate(" + ChartSettings.left + "," + ChartSettings.top + ")");

      // create x and y axes
      chart.append("g").attr("class", "xaxis").attr("transform", "translate(0," + ChartSettings.height + ")");
      chart.append("g").attr("class", "yaxis");

      // messages we may want to overlay on the chart
      chart.append("text").attr(
        "transform",
        "translate(" + ((ChartSettings.width / 2) - ChartSettings.messageLeft) +
        ", " + (ChartSettings.height - ChartSettings.messageBottom) + ")"
      ).classed("message hidden", true);

      // This is a list of answer ids, kept in order that they appear in the results instead of sorted by answer id.
      // Keeping the order as they are inserted is important so that the colors don't change as new answer ids appear.
      colorDomain = [];
    }

    /**
     * Calculate count data for each answer id for all responses.
     * The returned array is sorted by lowercase answer id.
     *
     * @param {Array} responses The response data as it comes from the REST API
     * @returns {Array} Aggregated responses. There is one response item per answer id and it includes the count
     */
    function makeHistogram(responses) {
      var lookup = {};
      var uniqueResponses = [];
      responses.forEach(function(response) {
        if (!(response.answer_id in lookup)) {
          lookup[response.answer_id] = 1;
          uniqueResponses.push(response);
        } else {
          lookup[response.answer_id] += 1;
        }
      });
      uniqueResponses = _.sortBy(uniqueResponses, function(response) {
        return response.answer_id.toLowerCase();
      });

      return uniqueResponses.map(function(response) {
        return {
          answer_id: response.answer_id,
          answer_text: response.answer_text,
          count: lookup[response.answer_id]
        };
      });
    }

    /**
     * Given the domain limits return some tick values, equally spaced out, all integers.
     * @param {number} domainMax The maximum domain value (the minimum is always 0).
     * @returns {Array} An array of integers within the domain used for tick values on the y axis
     */
    function makeIntegerTicks(domainMax) {
      var increment = Math.ceil(domainMax / ChartSettings.numYAxisTicks);
      return _.range(0, domainMax, increment);
    }

    /**
     * SVG doesn't have a capability to wrap text except for foreignObject which is not supported in IE11.
     * So we have to calculate it manually for X axis tick labels.
     * See https://bl.ocks.org/mbostock/7555321 for inspiration
     *
     * @param {selector} textSelector A D3 selector for x axis text elements
     * @param {number} barWidth The width of a bar
     * @param {string} text The text for the axis label
     */
    function wrapText(textSelector, barWidth, text) {
      textSelector.each(function() {
        var root = d3.select(this);

        var rootY = root.attr("y");
        var rootDy = parseFloat(root.attr("dy"));

        root.selectAll("tspan").remove();
        var words = text.split(/\s+/);
        var tspan = root.append("tspan").attr("x", 0).attr("y", rootY).attr("dy", rootDy + "em");

        var currentLine = 0;
        var lineHeight = 1.1;
        words.forEach(function(word) {
          if (!word) {
            // May happen if the input text is empty.
            return;
          }

          var tspanText = tspan.text();
          tspan.text(tspanText + " " + word);
          if (tspan.node().getComputedTextLength() > barWidth) {
            // The new word would go beyond the bar width boundary,
            // so change tspan back to its old text and create one with the
            // new word on a new line.
            currentLine++;
            tspan.text(tspanText + " ");
            tspan = root.append("tspan").attr("x", 0).attr("y", rootY).attr(
              "dy", ((currentLine * lineHeight) + rootDy) + "em"
            ).text(word);
          }
        });
      });
    }

    /**
     * Renders the graph and adjusts axes based on responses to the given problem.
     *
     * @param {Object} state The current rendering state
     */
    function renderD3(state) {
      var message = chart.select(".message");
      var responses = state.responses;
      if (responses.length === 0) {
        message.text(ChartSettings.noDataMessage).classed("hidden", false);
      } else {
        message.classed("hidden", true);
      }

      // Compute responses into information suitable for a bar graph.
      var histogram = makeHistogram(responses);
      var histogramAnswerIds = histogram.map(_.pluck(histogram, 'answer_id'));
      var histogramLookup = _.object(_.map(histogram, function(item) {
        return [item.answer_id, item];
      }));

      // Add answer ids to the color domain if they don't already exist
      colorDomain = _.union(colorDomain, histogramAnswerIds);

      // Create x scale to map answer ids to bar x coordinate locations. Note that
      // histogram was previously sorted in order of the lowercase answer id.
      var x = d3.scaleBand().rangeRound([0, ChartSettings.width]).padding(0.1).domain(
        histogramAnswerIds
      );
      // Create y scale to map response count to y coordinate for the top of the bar.
      var y = d3.scaleLinear().rangeRound([ChartSettings.height, 0]).domain(
        // pick the maximum count so we know how high the bar chart should go
        [0, d3.max(histogram, function(item) {
          return item.count;
        })]
      );
      // Create a color scale similar to the x scale to provide colors for each bar
      var color = d3.scaleOrdinal(d3.schemeCategory10).domain(colorDomain);

      // The D3 data join. This matches the histogram data to the rect elements
      // (there is a __data__ attribute on each rect keeping track of this). Also tell D3 to use the answer_id to make
      // this match.
      var bars = chart.selectAll("rect").data(histogram, function(item) {
        return item.answer_id;
      });


      // Set the position and color attributes for the bars. Note that there is a transition applied
      // for the y axis for existing bars being updated.
      bars.enter()
        // Everything in between enter() and merge(bars) applies only to new bars. This creates a new rect.
        .append("rect").attr("class", "bar")
        // Set the height and y values according to the scale. This prevents weird transition behavior
        // where new bars appear to zap in out of nowhere.
        .attr("y", function(response) { return y(response.count); })
        .attr("height", function(response) {
          return ChartSettings.height - y(response.count);
        })
        .merge(bars)
        // Now, for all bars, set the width and x values. No transition is applied for the x axis,
        // partially because of technical difficulties with the x axis labels and partially because
        // it looks strange to me
        .attr("x", function(response) { return x(response.answer_id); })
        .attr("width", x.bandwidth())
        .attr("fill", function(response) {
          return color(response.answer_id);
        })
        .transition()
        // Set a transition for the y axis for bars so that we have a slick update.
        .attr("y", function(response) { return y(response.count); })
        .attr("height", function(response) {
          return ChartSettings.height - y(response.count);
        });

      // If the responses disappear from the API such that there is no information for the bar
      // (probably shouldn't happen),
      // remove the corresponding rect element.
      bars.exit().remove();

      // Update the X axis
      chart.select(".xaxis")
        .call(
          d3.axisBottom(x).tickFormat(function() {
            // Override tick label formatting to make it blank. To fix word wrap we need to do this manually below.
            return null;
          })
        )
        .selectAll(".tick text")
        .each(function(answerId, i, nodes) {
          var response = histogramLookup[answerId];
          var answerText = response ? response.answer_text : "";
          wrapText(d3.select(nodes[i]), x.bandwidth(), answerText);
        });


      // Update the Y axis.
      // By default it assumes a continuous scale, but we just want to show integers so we need to create the ticks
      // manually.
      var yDomainMax = y.domain()[1];
      // May be NaN if the responses are empty
      var yTickValues = !isNaN(yDomainMax) ? makeIntegerTicks(y.domain()[1]) : [];
      chart.select(".yaxis")
        .transition() // transition to match the bar update
        .call(
          d3.axisLeft(y).tickValues(yTickValues).tickFormat(d3.format("d"))
        );
    }

    /**
     * Read from the responses API and put the new value in the rendering state.
     * If the problem is open, schedule another poll using this function.
     */
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
      Object.assign(state, {
        is_open: block.attr('data-open') === 'True',
        is_staff: block.attr('data-staff') === 'True'
      });
      initD3();
      render();

      if (state.is_staff) {
        pollForResponses();
      }
    });
  }

  function initializeRapidResponseAside(runtime, element) {
    return new RapidResponseAsideView(runtime, element);
  }

  window.RapidResponseAsideInit = initializeRapidResponseAside;
}($, _));
