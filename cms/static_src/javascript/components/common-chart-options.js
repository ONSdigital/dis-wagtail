/* this contains global options for all charts */
import ChartConstants from './chart-constants';

class CommonChartOptions {
  constructor(theme, title, type) {
    this.constants = ChartConstants.constants();

    // These options can be set globally for all charts
    this.options = {
      colors: theme === 'primary' ? this.constants.primaryTheme : this.constants.alternateTheme,
      chart: {
        backgroundColor: 'transparent',
        style: {
          fontFamily: '"OpenSans", "Helvetica Neue", arial, sans-serif',
          color: '#222222',
        },
      },
      legend: {
        align: 'left',
        verticalAlign: 'top',
        layout: 'horizontal',
        symbolWidth: type === 'line' ? 20 : 12,
        symbolHeight: type === 'line' ? 3 : 12,
        margin: 30,
        itemStyle: {
          color: this.constants.labelColor,
          fontSize: this.constants.desktopFontSize,
          fontWeight: 'normal',
        },
      },
      // chart title is rendered in wagtail
      title: {
        text: '',
      },
      lang: {
        accessibility: {
          chartContainerLabel: title,
        },
      },
      credits: {
        // Remove Highcharts watermark
        enabled: false,
      },
      // disabled the download button for now
      navigation: {
        buttonOptions: {
          enabled: false,
        },
      },
      yAxis: {
        labels: {
          style: {
            color: this.constants.axisLabelColor,
            fontSize: this.constants.desktopFontSize,
          },
        },
        lineColor: this.constants.gridLineColor,
        gridLineColor: this.constants.gridLineColor,
        zeroLineColor: this.constants.zeroLineColor,
      },
      xAxis: {
        labels: {
          style: {
            color: this.constants.axisLabelColor,
            fontSize: this.constants.desktopFontSize,
          },
        },
        lineColor: this.constants.gridLineColor,
        gridLineColor: this.constants.gridLineColor,
        zeroLineColor: this.constants.zeroLineColor,
        // Add tick marks
        tickWidth: 1,
        tickLength: 6,
        tickColor: this.constants.gridLineColor,
      },
      // Adjust font size for smaller width of chart
      // Note this is not the same as the viewport width
      responsive: {
        rules: [
          {
            condition: {
              maxWidth: 400,
            },
            chartOptions: {
              legend: {
                itemStyle: {
                  fontSize: this.constants.mobileFontSize,
                },
              },
              xAxis: {
                labels: {
                  style: {
                    fontSize: this.constants.mobileFontSize,
                  },
                },
              },
              yAxis: {
                labels: {
                  style: {
                    fontSize: this.constants.mobileFontSize,
                  },
                },
              },
            },
          },
        ],
      },
    };
  }

  getOptions() {
    return this.options;
  }

  getAnnotationLabelOptions() {
    return {
      style: {
        color: this.constants.axisLabelColor,
        fontSize: this.constants.desktopFontSize,
      },
      borderWidth: 0,
      backgroundColor: undefined,
    };
  }
}

export default CommonChartOptions;
