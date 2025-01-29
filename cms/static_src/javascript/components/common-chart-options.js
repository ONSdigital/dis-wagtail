class ChartOptions {
  static options() {
    return this.options;
  }

  constructor(theme, title, type) {
    // Primary theme colours from https://service-manual.ons.gov.uk/data-visualisation/colours/using-colours-in-charts
    const primaryTheme = [
      '#206095',
      '#27a0cc',
      '#003c57',
      '#118c7b',
      '#a8bd3a',
      '#871a5b',
      '#f66068',
      '#746cb1',
      '#22d0b6',
    ];
    // Alternate theme colours from https://service-manual.ons.gov.uk/data-visualisation/colours/using-colours-in-charts
    const alternateTheme = ['#206095', '#27A0CC', '#871A5B', '#A8BD3A', '#F66068'];
    const labelColor = '#414042';
    const axisLabelColor = '#707071';
    const gridLineColor = '#d9d9d9';
    const zeroLineColor = '#b3b3b3';
    // Responsive font sizes
    const mobileFontSize = '0.875rem';
    const desktopFontSize = '1rem';

    // These options can be set globally for all charts
    this.options = {
      colors: theme === 'primary' ? primaryTheme : alternateTheme,
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
          color: labelColor,
          fontSize: desktopFontSize,
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
      plotOptions: {
        bar: {
          // Set the width of the bars to be 30px and the spacing between them to be 10px
          pointWidth: 30, // Fixed bar height
          groupPadding: 0, // No padding between groups
          pointPadding: 0, // No padding within groups
          borderWidth: 0,
          borderRadius: 0,
          spacing: [10, 0, 0, 0], // [top, right, bottom, left] spacing between bars
          // Set the data labels to be enabled and positioned outside the bars
          // We can add custom formatting on each chart to move the labels inside the bars if the bar is wide enough
          dataLabels: {
            enabled: true,
            inside: false,
            style: {
              textOutline: 'none',
              // there is no semibold font weight available in the design system fonts, so we use 400 instead
              fontWeight: '400',
              color: labelColor,
              fontSize: mobileFontSize,
            },
          },
        },
        line: {
          lineWidth: 3, // Sets the line thickness to 3px
          linecap: 'round',
          marker: {
            enabled: false,
          },
          states: {
            hover: {
              lineWidth: 3, // Maintain line width on hover
            },
          },
        },
        column: {
          groupPadding: 0.2,
          borderWidth: 0,
          borderRadius: 0,
        },
      },
      yAxis: {
        labels: {
          style: {
            color: axisLabelColor,
            fontSize: desktopFontSize,
          },
        },
        lineColor: gridLineColor,
        gridLineColor: gridLineColor,
        zeroLineColor: zeroLineColor,
      },
      xAxis: {
        labels: {
          style: {
            color: axisLabelColor,
            fontSize: desktopFontSize,
          },
        },
        lineColor: gridLineColor,
        gridLineColor: gridLineColor,
        zeroLineColor: zeroLineColor,
        // Add tick marks
        tickWidth: 1,
        tickLength: 6,
        tickColor: gridLineColor,
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
                  fontSize: mobileFontSize,
                },
              },
              xAxis: {
                labels: {
                  style: {
                    fontSize: mobileFontSize,
                  },
                },
              },
              yAxis: {
                labels: {
                  style: {
                    fontSize: mobileFontSize,
                  },
                },
              },
            },
          },
        ],
      },
    };
  }
}

export default ChartOptions;
