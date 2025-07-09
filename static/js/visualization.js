// Load Gantt Chart
function loadGanttChart() {
    var tasks = ganttData.map(d => ({
        x: [d.Start, d.Finish],
        y: [d.Machine, d.Machine],
        mode: 'lines',
        line: { width: 20 },
        name: d.Task
    }));

    var layout = {
        title: 'Job Scheduling Timeline',
        xaxis: { title: 'Time' },
        yaxis: { title: 'Machines', autorange: 'reversed' },
        height: 500
    };

    Plotly.newPlot('gantt_chart', tasks, layout);
}

// Load Machine Utilization Pie Chart
function loadUtilizationChart() {
    var data = [{
        values: utilizationData.map(d => d.Utilization),
        labels: utilizationData.map(d => d.Machine),
        type: 'pie'
    }];

    var layout = {
        title: 'Machine Utilization Share',
        height: 500
    };

    Plotly.newPlot('utilization_chart', data, layout);
}

// Load Breakdown Alerts
function loadBreakdownAlerts() {
    var alertsDiv = document.getElementById("alerts_list");
    alertsDiv.innerHTML = "";
    breakdowns.forEach(alert => {
        var p = document.createElement('p');
        p.textContent = alert;
        alertsDiv.appendChild(p);
    });
}

// Load Rescheduling Info
function loadReschedulingList() {
    var rescheduleDiv = document.getElementById("rescheduling_list");
    rescheduleDiv.innerHTML = "";
    rescheduledJobs.forEach(job => {
        var p = document.createElement('p');
        p.textContent = job;
        rescheduleDiv.appendChild(p);
    });
}

// Load Final Schedule Table
function loadFinalScheduleTable() {
    var tableDiv = document.getElementById("final_schedule_table");
    tableDiv.innerHTML = "";

    var table = document.createElement('table');
    table.style.width = '100%';
    table.style.borderCollapse = 'collapse';

    // Table Header
    var thead = document.createElement('thead');
    var headerRow = document.createElement('tr');
    ["Job", "Machine", "Start Time", "End Time"].forEach(text => {
        var th = document.createElement('th');
        th.textContent = text;
        th.style.border = '1px solid black';
        th.style.padding = '8px';
        th.style.backgroundColor = '#f2f2f2';
        headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    // Table Body
    var tbody = document.createElement('tbody');
    finalSchedule.forEach(item => {
        var row = document.createElement('tr');
        Object.values(item).forEach(text => {
            var td = document.createElement('td');
            td.textContent = text;
            td.style.border = '1px solid black';
            td.style.padding = '8px';
            row.appendChild(td);
        });
        tbody.appendChild(row);
    });
    table.appendChild(tbody);

    tableDiv.appendChild(table);
}

// Load everything when page loads
window.onload = function() {
    loadGanttChart();
    loadUtilizationChart();
    loadBreakdownAlerts();
    loadReschedulingList();
    loadFinalScheduleTable();
}
