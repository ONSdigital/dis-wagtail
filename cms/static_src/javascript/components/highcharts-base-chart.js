/* global Highcharts */
import ChartOptions from './common-chart-options';

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
    this.apiConfig = JSON.parse(this.node.querySelector(`#config--${chartId}`).textContent);
    this.chartOptions = new ChartOptions(this.theme, this.title, this.chartType);
    if (this.chartType === 'bar') {
      this.updateBarChartHeight();
      this.postLoadDataLabels();
    }
    Highcharts.setOptions(this.chartOptions.options);
    Highcharts.chart(chartNode, this.apiConfig);
  }

  updateBarChartHeight() {
    // dynamically set the height of the chart based on the number of categories. Bars are 30px wide, with 10px spacing, so we allow 40px per bar, with an extra 100px for margins.
    // Todo: Needs more fine tuning, e.g. calculating the height of the legend
    this.chartOptions.options.chart.height = this.apiConfig.xAxis.categories.length * 40 + 100;
  }

  // For this to work, we need an option to include data lables and a format for them
  postLoadDataLabels() {
    this.chartOptions.options.chart.events = {
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
}

export default HighchartsBaseChart;
