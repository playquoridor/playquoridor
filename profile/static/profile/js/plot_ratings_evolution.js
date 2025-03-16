const ratingListInput = document.currentScript.dataset.ratingstable;
const ratingColumns = JSON.parse(document.currentScript.dataset.ratingscolumns.replace(/'/g, '"'));

// Replace single quotes with double quotes for strings
let jsonString = ratingListInput.replace(/'([^']*)'/g, '"$1"');

jsonString = jsonString.replace(/'([^']*)'/g, '"$1"');

// Add commas between the inner arrays
jsonString = jsonString.replace(/\]\s+\[/g, "],[");

// Add commas between the elements within the inner arrays
jsonString = jsonString.replace(/(\S+) (\d|^nan$)/g, "$1, $2");
jsonString = jsonString.replace(/(\d) (nan)/g, "$1, $2");
jsonString = jsonString.replace(/(nan) (nan)/g, "$1, $2");
// jsonString = jsonString.replace(/(\d|^nan$) (\S+) /g, "$1, $2");
// jsonString = jsonString.replace(/(\d|^nan$) (\d|^nan$)/g, "$1, $2");
jsonString = jsonString.replace(/\bnan\b/g, "null")

// Add commas between the inner arrays
// jsonString = '[["2023-12-23", 1500, 1500], ["2023-12-24", 1344, 1662], ["2023-12-29", 1244, 1962], ["2024-3-29", 1644, 2062]]'
const ratingList = JSON.parse(jsonString);

if (ratingList.length > 0){
    // Has rated games

    google.charts.load('current', {'packages':['corechart']});
    //google.charts.setOnLoadCallback(drawChart);

    function drawChart() {
        var data = new google.visualization.DataTable();
        data.addColumn('date', 'day');
        for (let v of ratingColumns.slice(1))
            data.addColumn('number', v);

        // Convert to dates
        var ratingListData = []
        for (const d of ratingList){
            let d_ = [new Date(d[0])]
            d_.push(...d.slice(1));
            ratingListData.push(d_);
        }
        data.addRows(ratingListData);

        var options = {
                curveType: 'function',
                // curveType: 'function',
            interpolateNulls: true,   //https://stackoverflow.com/questions/41767578/google-visualisation-line-chart-multiple-lines
            legend: { position: 'bottom' },
            //width: 500,
            // height: 250,
            'chartArea': {'right': 50,
                'left': 50,
                'top': 5,
                'width': '100%',
                'height': '80%'},
            hAxis: {
                format: 'd/M/yy',
                //ticks: getTicks(data),
                //gridlines: {count: 3}
            },
            vAxis: {
                // gridlines: {color: 'none'},
                //minValue: 0
            },
            backgroundColor: { fill:'#f9f9f9' }
        };

        // var chart = new google.charts.Line(document.getElementById('chart_container'));
        // chart.draw(data, google.charts.Line.convertOptions(options));
        var chart = new google.visualization.LineChart(document.getElementById('chart_container'));
        chart.draw(data, options);
    }


    window.onresize = function (){
        drawChart();
    };
    window.onload = function (){
        drawChart();
    }
}

/*
    var data = new google.visualization.DataTable();
    data.addColumn('number', 'Day');
    data.addColumn('number', 'Guardians of the Galaxy');
    data.addColumn('number', 'The Avengers');
    data.addColumn('number', 'Transformers: Age of Extinction');

data.addRows([
    [1,  37.8, 80.8, 41.8],
    [2,  30.9, 69.5, 32.4],
    [3,  25.4,   57, 25.7],
    [4,  11.7, 18.8, 10.5],
    [5,  11.9, 17.6, 10.4],
    [6,   8.8, 13.6,  7.7],
    [7,   7.6, 12.3,  9.6],
    [8,  12.3, 29.2, 10.6],
    [9,  16.9, 42.9, 14.8],
    [10, 12.8, 30.9, 11.6],
    [11,  5.3,  7.9,  4.7],
    [12,  6.6,  8.4,  5.2],
    [13,  4.8,  6.3,  3.6],
    [14,  4.2,  6.2,  3.4]
    ]);
 */
