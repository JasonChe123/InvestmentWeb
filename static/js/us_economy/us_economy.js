$(document).ready(function () {
    const scriptTag = $('#index-js');
    const chartT10Y2YData = JSON.parse(scriptTag.attr('chart-t10y2y-data'));
    const chartT10Y2YxAxisLabel = JSON.parse(scriptTag.attr('chart-t10y2y-x-axis-label'));
    let dataMax = Math.abs(Math.max.apply(Math, chartT10Y2YData));
    let dataMin = Math.abs(Math.min.apply(Math, chartT10Y2YData));
    let zeroStopPercent = dataMax / (dataMax + dataMin) * 100;

    let options = {
        chart: {
            id: 't10y2y',
            type: 'area',
            zoom: {
                enabled: true
            },
            background: 'transparent',
        },
        dataLabels: {
            enabled: false,
        },
        fill: {
            type: "gradient",
            gradient: {
                type: 'vertical',
                colorStops:
                    [
                        {
                            offset: 0,
                            color: '#1ee0ac',
                            opacity: 0
                        },
                        {
                            offset: zeroStopPercent,
                            color: '#1ee0ac',
                            opacity: 0.3
                        },
                        {
                            offset: zeroStopPercent,
                            color: '#e85347',
                            opacity: 0.3
                        },
                        {
                            offset: 100,
                            color: '#e85347',
                            opacity: 0
                        },
                    ]
            }
        },
        grid: {
            show: true,
            borderColor: 'rgba(123, 123, 123, 0.2)',
        },
        series: [{
            name: "t10y2y",
            data: chartT10Y2YData,
        }],
        stroke: {
            curve: 'straight',
            width: 1,
        },
        theme: {
            mode: 'light',
            palette: 'palette1',
            monochrome: {
                enabled: false,
                color: '#255aee',
                shadeTo: 'light',
                shadeIntensity: 0.65
            },
        },
        xaxis: {
            categories: chartT10Y2YxAxisLabel,
            tickAmount: 10,
            tickPlacement: 'on',
            axisBorder: {
                show: true,
                color: 'grey',
            },
            axisTicks: {
                show: false,
            }
        },
        yaxis: {
            axisBorder: {
                show: true,
                color: 'grey',
            },
            axisTicks: {
                show: false,
            },
        },
    };

    let chart = new ApexCharts(document.querySelector("#chart-t10y2y"), options);
    chart.render();
});


function createChartT10Y2Y() {

}