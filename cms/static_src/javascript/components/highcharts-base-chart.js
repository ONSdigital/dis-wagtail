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

    this.commonChartOptions = new CommonChartOptions(this.theme, this.title, this.chartType);

    // Configure the chart styling options common to all charts
    // Will only run once per page load
    this.setCommonChartOptions();

    if (this.chartType === 'bar') {
      this.updateBarChartHeight();
      this.postLoadDataLabels();
    }

    // Configure any annotations that have been specified
    if (this.annotationsValues) {
      this.configureAnnotations();
    }

    // Create the chart
    Highcharts.chart(chartNode, this.apiConfig);
  }

  // Set up the global Highcharts options
  setCommonChartOptions() {
    if (window.commonChartOptionsSet === undefined) {
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
    }
    window.commonChartOptionsSet = true;
  }

  updateBarChartHeight() {
    // dynamically set the height of the chart based on the number of categories. Bars are 30px wide, with 10px spacing, so we allow 40px per bar, with an extra 100px for margins.
    // Todo: Needs more fine tuning, e.g. calculating the height of the legend
    this.apiConfig.chart.height = this.apiConfig.xAxis.categories.length * 40 + 100;
  }

  // Updates the config to move the data labels inside the bars, but only if the bar is wide enough
  // This may also need to run when the chart is resized
  postLoadDataLabels() {
    this.apiConfig.chart.events = {
      // Move data labels inside bars if the bar is wide enough
      load() {
        const points = this.series[0].data;
        const options = {
          dataLabels: {
            inside: true,
            align: 'right',
            verticalAlign: 'middle',
            style: {
              color: 'white',
            },
          },
        };

        points.forEach((point) => {
          if (point.shapeArgs.height > 50) {
            point.update(options, false);
          }
        });

        this.redraw();
      },
    };
  }

  // Updates the config object to include any annotations that have been specified
  configureAnnotations() {
    const allAnnotations = [];
    this.annotationsValues.forEach((annotation) => {
      const annotationConfig = { labels: [], shapes: [] };
      annotationConfig.draggable = '';
      annotationConfig.labelOptions = this.commonChartOptions.getAnnotationLabelOptions();
      annotationConfig.labels.push({
        text: annotation.text,
        point: {
          x: annotation.xValue,
          y: 20, // hard coded to be 20px from the top of the chart
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
      allAnnotations.push(annotationConfig);
    });
    this.apiConfig.annotations = allAnnotations;
  }
}

export default HighchartsBaseChart;
