$(document).ready(function () {
    if ($("#performance-chart").length > 0) {
        main();
    }
});

function main() {
    let scriptTag = $('#longshort-chart-js');
    let data = JSON.parse(scriptTag.attr('chartData'));
    let dataKey = Object.keys(data);
    let totalCount = dataKey.filter(key => key.includes("Total")).length;
    const xValues = data['date'];
    let datasets = [];
    let darkThemeLongColor = "rgba(130, 130, 255, 0.3)";
    let darkThemeShortColor = "rgba(255, 130, 130, 0.3)";
    let darkThemeTotalColor = "rgba(130, 255, 130, 1.0)";
    let lightThemeLongColor = "rgba(130, 130, 255, 0.3)";
    let lightThemeShortColor = "rgba(255, 130, 130, 0.3)";
    let lightThemeTotalColor = "rgba(130, 255, 130, 1.0)";
    let darkThemeSP500Color = "#ffffff";
    let lightThemeSP500Color = "#000000";

    // Iterate over the keys to create datasets dynamically
    dataKey.forEach((key, index) => {
        if (key !== 'date') {
            let label = key.replace(/_/g, ' ');

            // Ignore Long/Short data if totalCount > 1
            if (totalCount > 1 && (key.includes("Long") || key.includes("Short"))) {
                return;
            }

            datasets.push({
                data: data[key],
                fill: false,
                label: totalCount > 1 ? label.replace(" Total", "") : label,
                lineTension: 0.2,
            });
        }
    });

    // Init chart
    let chart = new Chart("performance-chart", {
        type: "line",
        data: {
            labels: xValues,
            datasets: datasets,
        },
        options: {
            legend: {
                display: true,
                labels: { fontSize: 14, fontCoor: '#000000' }
            },
            scales: {
                yAxes: [{
                    gridLines: { color: "rgba(130, 130, 130, 0.2)" },
                    ticks: {
                        autoSkip: true,
                        maxTicksLimit: 10,
                    },
                }],
                xAxes: [{
                    gridLines: { color: "rgba(130, 130, 130, 0.2)" },
                    ticks: {
                        autoSkip: true,
                        maxTicksLimit: 10,
                    },
                }],
            },
            title: {
                display: true,
                text: scriptTag.attr("selectedMethod").trim() + " vs S&P 500",
                fontSize: 16,
                fontColor: '#000000',
            }
        }
    });

    // Update chart theme
    function updateChartTheme(isDark) {
        chart.options.scales.yAxes[0].ticks.fontColor = isDark ? '#ffffff' : '#000000';
        chart.options.scales.xAxes[0].ticks.fontColor = isDark ? '#ffffff' : '#000000';
        chart.data.datasets.forEach((dataset, index) => {
            let ref = index + 1;

            if (dataset.label.includes('Long')) {
                // Set color for long position
                dataset.borderColor = isDark ? darkThemeLongColor : lightThemeLongColor;

            } else if (dataset.label.includes('Short')) {
                // Set color for short position
                dataset.borderColor = isDark ? darkThemeShortColor : lightThemeShortColor;

            } else if (dataset.label.includes('S&P 500')) {
                // Set color for short position
                dataset.borderColor = isDark ? darkThemeSP500Color : lightThemeSP500Color;

            } else {
                // Set color for total position
                if (totalCount > 1) {
                    dataset.borderColor = `rgba(${ref * 120 % 255}, ${ref * 150 % 255}, ${ref * 180 % 255}, 1.0)`;
                    dataset.backgroundColor = `rgba(${ref * 120 % 255}, ${ref * 150 % 255}, ${ref * 180 % 255}, 0.5)`;
                } else {
                    dataset.borderColor = isDark ? darkThemeTotalColor : lightThemeTotalColor;
                }
            }
        });
        chart.options.title.fontColor = isDark ? '#ffffff' : '#000000';
        chart.options.legend.labels.fontColor = isDark ? '#ffffff' : '#000000';
        chart.update();
    }

    // Detect current theme
    function isDarkTheme() {
        return localStorage.getItem('theme') === 'dark';
    }

    // Event listener for theme switch button
    $('.theme-toggle').click(function () {
        const isDark = isDarkTheme();
        updateChartTheme(!isDark);
    });

    // Set theme in line with current theme
    const isDark = isDarkTheme();
    updateChartTheme(isDark);
}