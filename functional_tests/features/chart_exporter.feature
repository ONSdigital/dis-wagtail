Feature: Chart images from the chart exporter

    Background:
        Given a superuser logs into the admin site
        And  a statistical article exists

    @chart_exporter_mock
    Scenario: A chart image rendered when the page is saved can be downloaded from the draft
        Given the statistical article page has a chart
        When the user views the statistical article page draft
        Then the chart image can be downloaded
        And  the chart exporter was asked to render the "line chart" chart

    @chart_exporter_mock
    Scenario: A chart has no image download when the chart exporter fails
        Given the chart exporter responds with "render_failed"
        And  the statistical article page has a chart
        When the user views the statistical article page draft
        Then the chart has no image download link
        And  the chart exporter was asked to render the "line chart" chart
