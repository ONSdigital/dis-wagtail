/* global Highcharts */
import CommonChartOptions from './common-chart-options';
import LineChartPlotOptions from './line-chart-plot-options';
import BarChartPlotOptions from './bar-chart-plot-options';
import ColumnChartPlotOptions from './column-chart-plot-options';

class HighchartsBaseChart {
  static selector() {
    return '[data-highcharts-base-chart]';
  }

  constructor(node) {
    this.node = node;
    this.chartType = this.node.dataset.highchartsType;
    this.theme = this.node.dataset.highchartsTheme;
    this.title = this.node.dataset.highchartsTitle;
    this.useStackedLayout = this.node.hasAttribute('data-highcharts-use-stacked-layout');
    const chartNode = this.node.querySelector('[data-highcharts-chart]');
    const chartId = chartNode.dataset.highchartsId;
    // We start with some config in the correct Highcharts format supplied by Wagtail
    // This gets some further modifications
    this.apiConfig = JSON.parse(this.node.querySelector(`#config--${chartId}`).textContent);
    if (this.node.querySelector(`#annotations-values--${chartId}`)) {
      this.annotationsValues = JSON.parse(
        this.node.querySelector(`#annotations-values--${chartId}`).textContent,
      );
    }

    // Hide data labels for clustered bar charts with more than 2 series
    if (
      this.chartType === 'bar' &&
      this.useStackedLayout === false &&
      this.apiConfig.series.length > 2
    ) {
      this.apiConfig.series.forEach((series) => {
        /* eslint-disable no-param-reassign */
        series.dataLabels = {
          enabled: false,
        };
        /* eslint-enable no-param-reassign */
      });
    }

    this.commonChartOptions = new CommonChartOptions(this.theme, this.title, this.chartType);

    // Configure the chart styling options common to all charts
    // Will only run once per page load
    this.setCommonChartOptions();

    // Configure any annotations that have been specified
    if (this.annotationsValues) {
      this.configureAnnotations();
    }

    this.apiConfig.chart.events = {};
    this.apiConfig.chart.events.load = (event) => {
      if (this.chartType === 'bar') {
        if (this.useStackedLayout === false) {
          this.updateBarChartHeight(event);
        }
        this.postLoadDataLabels(event);
      }
    };

    // Create the chart
    Highcharts.chart(chartNode, this.apiConfig);
  }

  // Set up the global Highcharts options
  setCommonChartOptions = () => {
    // currently set each time a chart is rendered as some options depend on the chart type
    const chartOptions = this.commonChartOptions.getOptions();
    chartOptions.plotOptions = new LineChartPlotOptions().plotOptions;
    chartOptions.plotOptions = {
      ...chartOptions.plotOptions,
      ...new BarChartPlotOptions().plotOptions,
    };
    chartOptions.plotOptions = {
      ...chartOptions.plotOptions,
      ...new ColumnChartPlotOptions().plotOptions,
    };

    // Apply the options globally
    Highcharts.setOptions(chartOptions);
  };

  // This updates the height of the vertical axis and overall chart to fit the number of categories
  // Note that the vertical axis on a bar chart is the x axis
  updateBarChartHeight = (event) => {
    const currentChart = event.target;
    const numberOfCategories = this.apiConfig.xAxis.categories.length;
    const numberOfSeries = currentChart.series.length; // Get number of bar series
    let barHeight = 30; // Height of each individual bar - set in bar-chart-plot-options
    let groupSpacing = 0; // Space we want between category groups, or betweeen series groups for cluster charts
    let categoriesTotalHeight = 0;
    let totalSpaceHeight = 0;
    if (numberOfSeries > 1) {
      // slighly lower bar height for cluster charts
      barHeight = 28;
      // for cluster charts there is no space between the bars within a series, and 14px between each series
      groupSpacing = 14;
      // lower barHeight for series with 3 categories or more
      if (numberOfSeries >= 3) {
        barHeight = 20;
      }
      categoriesTotalHeight = numberOfCategories * barHeight * numberOfSeries;

      totalSpaceHeight = numberOfCategories * groupSpacing;
      // work out the group padding for cluster charts which is measured in xAxis units.
      const plotHeight = categoriesTotalHeight + totalSpaceHeight;
      const xUnitHeight = plotHeight / numberOfCategories;
      const groupPadding = groupSpacing / 2 / xUnitHeight;
      currentChart.series.forEach((series) => {
        series.update({
          groupPadding: groupPadding,
          pointWidth: barHeight,
        });
      });
    } else {
      groupSpacing = 10;
      categoriesTotalHeight = numberOfCategories * barHeight;
      totalSpaceHeight = (numberOfCategories - 1) * groupSpacing;
    }

    this.apiConfig.xAxis.height = categoriesTotalHeight + totalSpaceHeight;
    const totalHeight =
      currentChart.plotTop + this.apiConfig.xAxis.height + currentChart.marginBottom;

    if (totalHeight !== currentChart.chartHeight) {
      currentChart.setSize(null, totalHeight, false);
    }

    currentChart.redraw();
  };

  // Updates the config to move the data labels inside the bars, but only if the bar is wide enough
  // This may also need to run when the chart is resized
  // Todo: adapt for stacked charts
  /* eslint-disable class-methods-use-this */
  postLoadDataLabels = (event) => {
    const currentChart = event.target;
    const points = currentChart.series[0].data;
    const options = {
      // to do: move this to common-chart-options and fetch from there
      dataLabels: {
        inside: true,
        align: 'right',
        verticalAlign: 'middle',
        style: {
          color: 'white',
          fontWeight: 'bold',
        },
      },
    };

    points.forEach((point) => {
      // Move the data labels inside the bar if the label is longer than 50px
      if (point.shapeArgs.height > 50) {
        point.update(options, false);
      }
    });

    currentChart.redraw();
  };
  /* eslint-enable class-methods-use-this */

  // Updates the config object to include any annotations that have been specified
  // Needs amending for bar charts
  configureAnnotations = () => {
    const annotationConfig = {
      draggable: '',
      labelOptions: this.commonChartOptions.getAnnotationLabelOptions(),
      labels: [],
      shapes: [],
    };

    this.annotationsValues.forEach((annotation) => {
      annotationConfig.labels.push({
        text: annotation.text,
        point: {
          x: annotation.xValue,
          // hard coded to be 20px from the top of the chart
          y: 20,
          xAxis: 0,
          yAxis: undefined, // allows the 20px offset to be relative to the overall chart, not to the y axis
        },
      });

      annotationConfig.shapes.push({
        type: 'path',
        points: [
          // the position of the top of the arrow
          {
            x: annotation.xValue,
            y: 30, // hard coded to be 10px from the label
            xAxis: 0,
          },
          // the position of the bottom of the arrow - at the point being labelled
          {
            x: annotation.xValue,
            y: annotation.yValue,
            xAxis: 0,
            yAxis: 0,
          },
        ],
        markerEnd: 'arrow',
        stroke: '#414042',
        strokeWidth: 1,
      });
    });

    this.apiConfig.annotations = [annotationConfig];
  };
}

export default HighchartsBaseChart;
