/* global Highcharts */
class HighchartsBaseChart {
  static selector() {
    return '[data-highcharts-base-chart]';
  }

  constructor(node) {
    this.node = node;
    const chartNode = this.node.querySelector('[data-highcharts-chart]');
    const chartId = chartNode.dataset.highchartsId;
    const config = JSON.parse(this.node.querySelector(`#config--${chartId}`).textContent);
    Highcharts.chart(chartNode, config);
  }
}

export default HighchartsBaseChart;
