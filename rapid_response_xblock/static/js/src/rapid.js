(function($, _) {
  'use strict';

  // time between polls of responses API
  var POLLING_MILLIS = 3000;
  // color palette for bars
  var PALETTE = [
    '#1e73ae',
    '#dddb32',
    '#2b9b2b',
    '#e1516f',
    '#08cdf1',
    '#a964d4',
    '#505050',
    '#f77b0e',
    '#472ecc',
    '#7cce40',
    '#876a16'
  ];
  // this sentinel value means no data should be shown
  var NONE_SELECTION = 'None';

  function RapidResponseAsideView(runtime, element) {
    var toggleStatusUrl = runtime.handlerUrl(element, 'toggle_block_open_status');
    var responsesUrl = runtime.handlerUrl(element, 'responses');
    var $element = $(element);

    var rapidTopLevelSel = '.rapid-response-block';
    var rapidBlockContentSel = '.rapid-response-content';
    var rapidBlockResultsSel = '.rapid-response-results';
    var problemStatusBtnSel = '.problem-status-toggle';
    var toggleTemplate = _.template($(element).find("#rapid-response-toggle-tmpl").text());

    // default values
    var state = {
      is_open: false,
      is_staff: false,
      runs: [],
      choices: [],
      counts: {},
      selectedRuns: [null]  // one per chart. null means select the latest one
    };

    /**
     * Render template
     */
    function render() {
      var $rapidBlockContent = $element.find(rapidBlockContentSel);
      $rapidBlockContent.html(toggleTemplate(state));
      renderChartContainer();

      $rapidBlockContent.find(problemStatusBtnSel).click(function() {
        $.post(toggleStatusUrl).then(
          function(newState) {
            // Selected runs should be reset when the open status is changed
            state = _.assign({}, state, newState, {
              selectedRuns: [null]
            });
            render();

            if (state.is_open) {
              pollForResponses();
            }
          }
        );
      });
    }

    // TODO: These values are guesses, maybe we want to calculate based on browser width/height? Not sure
    var ChartSettings = {
      top: 50, // space for text for upper label on y axis
      left: 50, // space for y axis
      right: 50, // space for text to flow
      bottom: 200, // space for x axis
      outerBufferWidth: 200, // pixels on the right and left
      outerTop: 100, // space between chart and top of container, should contain enough space for buttons
      innerBufferWidth: 0, // space between two charts
      numYAxisTicks: 6,
      minChartWidth: 400,
      maxChartWidth: 1300,
      minChartHeight: 500,
      maxChartHeight: 800
    };

    /**
     * Given the domain limits return some tick values, equally spaced out, all integers.
     * @param {number} domainMax The maximum domain value (the minimum is always 0).
     * @returns {Array} An array of integers within the domain used for tick values on the y axis
     */
    function makeIntegerTicks(domainMax) {
      var increment = Math.ceil(domainMax / ChartSettings.numYAxisTicks);
      return _.range(0, domainMax + 1, increment);
    }

    /**
     * Calculate width of a chart given the number of charts and the browser width
     *
     * @returns {number} Chart width in pixels
     */
    function calcChartWidth() {
      var browserWidth = $(window).width();
      var numCharts = state.selectedRuns.length;
      return Math.max(
        ChartSettings.minChartWidth,
        Math.min(
          ChartSettings.maxChartWidth,
          ((browserWidth - ChartSettings.outerBufferWidth) / numCharts) -
          (ChartSettings.innerBufferWidth * (numCharts - 1))
        )
      );
    }

    /**
     * Calculate height of a chart given the browser width
     *
     * @returns {number} Chart height in pixels
     */
    function calcChartHeight() {
      var browserHeight = $(window).height();
      return Math.max(
        ChartSettings.minChartHeight,
        Math.min(
          ChartSettings.maxChartHeight,
          browserHeight - ChartSettings.outerTop
        )
      );
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
        // This is a g.tick item
        var root = d3.select(this);
        var rootText = root.select("text");

        var rootY = rootText.attr("y");
        var rootDy = parseFloat(rootText.attr("dy"));
        rootText.remove();
        root.select("g").remove();

        var angle = 30;
        var radians = angle * Math.PI / 180;
        // yay trig
        // this value is the maximum length for the text when laid out at an angle
        // hypotenuse is divided in half since text is starting in center
        var maxTextWidth = (barWidth / Math.cos(radians)) / 2;
        var rootContainer = root.append("g").attr("transform", "rotate(" + angle + ", 0, 10)");
        rootText = rootContainer.append("text")
          .attr("fill", "#000")
          .attr("text-anchor", "start")
          .attr("dy", rootDy + "em")
          .attr("y", rootY);

        var words = text.split(/\s+/);
        var tspan = rootText.append("tspan").attr("x", 0).attr("y", rootY).attr("dy", rootDy + "em");

        var currentLine = 0;
        var lineHeight = 1.1;
        // Build the text word by word so that it breaks lines appropriately
        // and cuts off with an ellipsis if it gets too long
        words.forEach(function(word) {
          if (!word) {
            // May happen if the input text is empty.
            return;
          }

          var compiledText = tspan.text();
          tspan.text(compiledText + " " + word);
          if (tspan.node().getComputedTextLength() > maxTextWidth) {
            // Check if the new word would go beyond the bar width boundary.

            // If this is the first word on the line we don't have a choice but to render it
            if (compiledText.length === 0) {
              return;
            }

            if (currentLine === 1) {
              // there is a maximum of two lines until we add the ellipses
              tspan.text(compiledText + "...");
              currentLine++;
              return;
            }

            if (currentLine > 1) {
              // maximum of two lines
              tspan.text(compiledText);
              return;
            }

            // Change tspan back to its old text and create a one with the
            // word on a new line.
            currentLine++;
            tspan.text(compiledText + " ");
            tspan = rootText.append("tspan").attr("x", 0).attr("y", rootY).attr(
              "dy", ((currentLine * lineHeight) + rootDy) + "em"
            ).text(word);
          }
        });
      });
    }

    /**
     * Click handler to close this chart
     * @param {number} chartIndex The index of the chart
     */
    function closeChart(chartIndex) {
      state.selectedRuns.splice(chartIndex, 1);
      render();
    }

    /**
     * Select handler to choose a different run for the chart
     * @param {number} chartIndex The index of the chart
     */
    function changeSelectedChart(chartIndex) {
      var selectedRun = this.value;
      if (selectedRun !== NONE_SELECTION) {
        selectedRun = parseInt(selectedRun);
      }
      state.selectedRuns[chartIndex] = selectedRun;
      render();
    }

    /**
     * Click handler to open a new chart for comparison
     */
    function openNewChart() {
      state.selectedRuns = [state.selectedRuns[0], NONE_SELECTION];
      render();
    }

    /**
     * Renders the container elements for the charts using D3
     */
    function renderChartContainer() {
      // Get the indexes for selected runs. This should either be [0] or [0, 1].
      var chartKeys = _.keys(state.selectedRuns);

      // D3 data join for charts. Create a container div for each chart to store graph, select element and buttons.
      var containers = d3.select(element)
        .select(rapidBlockResultsSel)
        .selectAll(".chart-container")
        .data(chartKeys);
      var newContainers = containers.enter()
        .append("div");

      // chart selection, close and compare buttons
      var selectionContainers = containers.selectAll(".selection-container");
      var newSelectionContainers = newContainers
        .append("div")
        .classed("selection-container", true);

      newSelectionContainers.append("select")
        .on('change', changeSelectedChart);

      newSelectionContainers.append("a")
        .classed("compare-responses", true)
        .text("Compare responses")
        .on("click", openNewChart);

      newSelectionContainers.append("a")
        .classed("close", true)
        .text("Close")
        .on('click', closeChart);

      var selectionRowsMerged = newSelectionContainers.merge(selectionContainers)
        .attr("style", "margin-left: " + ChartSettings.left + "px");
      selectionRowsMerged.selectAll(".compare-responses").classed("hidden", function() {
        return chartKeys.length !== 1 || state.is_open || state.runs.length < 2;
      });
      selectionRowsMerged.selectAll(".close").classed("hidden", function() {
        return chartKeys.length === 1;
      });

      // create the chart svg container
      var newCharts = newContainers
        .append("svg")
        // The g element has a little bit of padding so the x and y axes can surround it
        .append("g").attr("class", "chart");
      // create x and y axes
      newCharts.append("g").attr("class", "xaxis");
      newCharts.append("g").attr("class", "yaxis");

      newContainers.merge(containers)
        .attr("class", "chart-container " + (chartKeys.length === 1 ? 'single-chart' : 'two-charts'))
        .each(function (index, __, charts) {
          renderChart(d3.select(charts[index]), index);
        })
        .selectAll("svg")
        .attr("width", calcChartWidth())
        .attr("height", calcChartHeight())
        .selectAll(".chart")
        .attr("transform", "translate(" + ChartSettings.left + "," + ChartSettings.top + ")")
        .select(".xaxis");

      // Remove charts if selectedRuns reduces in size.
      // We don't need to do this for all the inner elements, the remove will propagate.
      containers.exit().remove();
    }

    /**
     * Render the chart in the container.
     *
     * @param {Object} container D3 selector for the chart container
     * @param {number} chartIndex The index of the chart (either 0 or 1)
     */
    function renderChart(container, chartIndex) {
      var runs = state.runs;
      var counts = state.counts;
      var choices = state.choices;
      var selectedRun = state.selectedRuns[chartIndex];

      // select the proper option and use it to filter the runs
      var select = container.select(".selection-container").select("select")
        .classed("hidden", state.runs.length === 0 || state.is_open);
      if (selectedRun === null && runs.length > 0) {
        // The newest run should be the most recent one according to the info received from the server.
        selectedRun = runs[0].id;
      }

      var histogram = choices.map(function (item) {
        return {
          answer_id: item.answer_id,
          answer_text: item.answer_text,
          count: counts[item.answer_id][selectedRun] || 0
        }
      });

      // D3 data join on runs to create a select list
      var optionData = [{ id: NONE_SELECTION }].concat(runs);
      var options = select.selectAll("option").data(optionData, function(run) {
        return run.id;
      });
      options.enter()
        .append("option")
        .merge(options)
        .attr("value", function(run) { return run.id; })
        .text(function(run) {
          if (run.id === NONE_SELECTION) {
            return (chartIndex > 0) ? 'Select' : 'None';
          }
          return moment(run.created).format("MMMM D, YYYY, h:mm:ss a");
        });
      options.exit().remove();

      select.enter().merge(select).property('value', selectedRun);

      // Compute responses into information suitable for a bar graph.
      var histogramAnswerIds = _.pluck(histogram, 'answer_id');
      var histogramLookup = _.object(_.map(histogram, function(item) {
        return [item.answer_id, item];
      }));

      // Create x scale to map answer ids to bar x coordinate locations. Note that
      // histogram was previously sorted in order of the lowercase answer id.
      var innerWidth = calcChartWidth() - ChartSettings.left - ChartSettings.right - ChartSettings.innerBufferWidth;
      var x = d3.scaleBand()
        .rangeRound([0, innerWidth])
        .padding(0.1)
        .domain(histogramAnswerIds);

      // Create y scale to map response count to y coordinate for the top of the bar.
      var innerHeight = calcChartHeight() - ChartSettings.top - ChartSettings.bottom;
      var y = d3.scaleLinear().rangeRound([innerHeight, 0]).domain(
        // pick the maximum count so we know how high the bar chart should go
        [0, d3.max(histogram, function(item) {
          return item.count;
        })]
      );
      // Create a color scale similar to the x scale to provide colors for each bar
      var color = d3.scaleOrdinal(PALETTE).domain(histogramAnswerIds);

      // The D3 data join. This matches the histogram data to the rect elements
      // (there is a __data__ attribute on each rect keeping track of this). Also tell D3 to use the answer_id to make
      // this match.
      var chart = container.select(".chart");
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
        .attr("x", function(response) { return x(response.answer_id); })
        .attr("width", x.bandwidth())
        .attr("y", function(response) { return y(response.count); })
        .attr("height", function(response) {
          return innerHeight - y(response.count);
        })
        .merge(bars)
        .attr("fill", function(response) {
          return color(response.answer_id);
        })
        .transition()
        // Set a transition for bars so that we have a slick update.
        .attr("x", function(response) { return x(response.answer_id); })
        .attr("width", x.bandwidth())
        .attr("y", function(response) { return y(response.count); })
        .attr("height", function(response) {
          return innerHeight - y(response.count);
        });

      // If the responses disappear from the API such that there is no information for the bar
      // (probably shouldn't happen),
      // remove the corresponding rect element.
      bars.exit().remove();

      // Update the X axis
      chart.select(".xaxis")
        .transition()
        .call(
          d3.axisBottom(x).tickFormat(function() {
            // Return null to output no text by default
            // The wrapText(...) call below will add text manually to let us adjust the angle and fit boundaries
            return null;
          })
        )
        .attr("transform", "translate(0," +
          (calcChartHeight() - ChartSettings.bottom - ChartSettings.top) +
        ")")
        .selectAll(".tick")
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
          d3.axisLeft(y)
            .tickValues(yTickValues)
            .tickFormat(d3.format("d"))
            // make the tick stretch to cover the entire chart
            .tickSize(-innerWidth)
        )
        .selectAll(".tick")
        // render the tick line as a dashed line
        .attr("stroke-dasharray", function(value) {
          // At 0 the line should be solid to blend in with the chart border
          return value === 0 ? null : "8,8";
        })
        .selectAll("line")
        .attr("stroke", "rgba(0,0,0,.3)");

      // strangely, the default path has a line at the side and one at the top
      // we just want the one on the side
      chart.select(".yaxis .domain").remove();
      // Render a vertical line at x=0
      chart.select(".yaxis")
        .append("line")
        .classed("line", true)
        .attr("stroke", "#000")
        .attr("x2", 0.5)
      chart.select(".yaxis .line")
        .transition()
        .attr("y2", innerHeight);
    }

    /**
     * Read from the responses API and put the new value in the rendering state.
     * If the problem is open, schedule another poll using this function.
     */
    function pollForResponses() {
      $.get(responsesUrl).then(function(newState) {
        state = _.assign({}, state, newState);

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
      _.assign(state, {
        is_open: block.attr('data-open') === 'True',
        is_staff: block.attr('data-staff') === 'True'
      });
      render();

      // adjust graph for each rerender
      window.addEventListener('resize', function() {
        render();
      });

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
