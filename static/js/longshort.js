document.addEventListener('DOMContentLoaded', function () {
    const csrf_token = document.querySelector("#csrf_token").value;
    const startBtn = document.querySelector("#startBtn");
    const amountInput = document.querySelector("#amount");
    const fileInput = document.querySelector("#formFile");
    const exportButton = document.querySelector("#export_button");
    const closeButton = document.querySelector("#close_button");
    const basketTraderModal = new bootstrap.Modal(document.getElementById('basketTraderModal'));
    const messageModal = new bootstrap.Modal(document.getElementById('messageModal'));
    const messageModalBody = document.getElementById('messageModalBody');
    const loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'));

    // Start button event handlers
    startBtn.addEventListener('click', function () {
        loadingModal.show();
        loadingModal.hide()
    });

    // Add selected method
    function addSelectedMethod(method) {
        const selected_method = document.getElementById("selected_method");
        const selected_method_input = document.getElementById("selected_method_input");

        // If the last string is +, -, *, /, (
        if (/[+\-*\/(]$/.test(selected_method.innerText)) {
            // Add the selected method
            selected_method.innerText += " " + method;
            selected_method_input.value += " " + method;
        }
        // If the string includes +, -, *, /
        else if (/[+\-*\/]/.test(selected_method.innerText)) {
            // If +, -, *, / and followed by not(+, -, *, /)
            const lastOperatorIndex = selected_method.innerText.search(/[+\-*\/][^+\-*/]*$/);
            if (lastOperatorIndex !== -1) {
                // Replace the last method string
                const newString = selected_method.innerText.slice(0, lastOperatorIndex + 2) + method;
                selected_method.innerText = newString;
                selected_method_input.value = newString;
            }
        }
        // Else
        else {
            selected_method.innerText = method;
            selected_method_input.value = method;
        }
    }

// Table formatting: add new-line before and after 'to' in all table headers
    const heads = document.getElementsByTagName('th');
    for (let i = 0; i < heads.length; i++) {
        heads[i].innerHTML = heads[i].innerHTML.replaceAll(" to ", "<br>to<br>");
    }

// Table formatting: change color to 'red' for negative values, and align all numbers to the right
    const cells = document.getElementsByTagName('td');
    for (let i = 0; i < cells.length; i++) {
        const value = parseFloat(cells[i].textContent);

        // Align all numbers to the right
        if (typeof (value) === 'number' && !isNaN(value)) {
            cells[i].style.textAlign = 'right';
        }

        // Change color of negative values
        if (!isNaN(value) && value < 0) {
            cells[i].style.color = 'red';
        }
    }

// Table formatting: add border to all tables
    const tables = document.getElementsByTagName('table');
    for (let i = 0; i < tables.length; i++) {
        tables[i].style.border = '1px solid #bbb';
    }

// Table formatting: add left border to all ticker columns
    for (let i = 0; i < heads.length; i++) {  // i starts from 1 because i need to ignore the first comlumn
        if (heads[i].textContent === 'Ticker') {
            const symbolColumnIndex = heads[i].cellIndex;
            heads[i].style.borderLeft = '1px solid #bbb';

            for (let j = 0; j < cells.length; j++) {
                if (cells[j].cellIndex === symbolColumnIndex) {
                    cells[j].style.borderLeft = '1px solid #bbb';
                }
            }
        }
    }

// Methods search bar
    const search_field = document.querySelector("#search-field");
    const search_result = document.querySelector("#search-result");
    search_result.style.display = "none";
    search_field.addEventListener('keyup', function (event) {
        const search_value = event.target.value;
        fetch("search-method", {
            method: "POST",
            headers: {
                "X-requested-with": "XMLHttpRequest",
                "Content-Type": "application/json",
                'X-CSRFToken': csrf_token,
            },
            body: JSON.stringify({"search_text": search_value})
        })
            .then(response => response.json())
            .then(data => {
                search_result.textContent = "";
                if (data.result.length > 0) {
                    // Show the dropdown result
                    search_result.style.display = "block";

                    // Loop over the result from server
                    for (let i = 0; i < data.result.length; i++) {
                        // Add result in dropdown
                        const link = document.createElement("a");
                        link.innerText = data.result[i];
                        link.classList.add("dropdown-item");
                        search_result.appendChild(link);

                        // Add click event
                        link.addEventListener('click', function () {
                            addSelectedMethod(data.result[i]);

                            // Initialize the search field
                            search_field.value = "";
                            search_result.textContent = "";

                            // Hide the dropdown result
                            search_result.style.display = "none";
                        });
                    }
                } else {
                    // Hide the dropdown result
                    search_result.style.display = "none";
                }
            });
    });

// Set value of selected method
    document.querySelectorAll('.method-selector').forEach(function (method_selector) {
        method_selector.addEventListener('change', function () {
            addSelectedMethod(this.value);
        });
    });

// Operator event
    const selected_method = document.getElementById("selected_method");
    const selected_method_input = document.getElementById("selected_method_input");
    document.querySelectorAll('.operator').forEach(function (operator) {
        operator.addEventListener('click', function () {
            // If the AC button was clicked
            if (this.value === "AC") {
                selected_method.innerText = "Please select a method...";
                selected_method_input.value = "";
                return;
            }

            // If buttons +, -, *, / were clicked
            if (/[+\-*/]/.test(this.value)) {
                // If the selected method is empty
                if (selected_method_input.value === "") return;

                // If the last string is '('
                if (/[(]$/.test(selected_method_input.value)) return;

                // If the last string is +, -, *, /
                if (/[+\-*/]$/.test(selected_method_input.value)) {
                    // Replace the last operator
                    selected_method.innerText = selected_method.innerText.slice(0, -1) + this.value;
                    selected_method_input.value = selected_method_input.value.slice(0, -1) + this.value;
                    return;
                }

                // Add operator
                selected_method.innerText += " " + this.value;
                selected_method_input.value += " " + this.value;
                return;
            }

            // If buttons '(' was clicked
            if (this.value === "(") {
                // If the selected method is empty
                if (selected_method_input.value === "") {
                    // Add operator
                    selected_method.innerText = this.value;
                    selected_method_input.value = this.value;
                }

                // If the last string is +, -, *, /
                else if (/[+\-*/]$/.test(selected_method_input.value)) {
                    // Add operator
                    selected_method.innerText += " " + this.value;
                    selected_method_input.value += " " + this.value;
                }
            }

            // If buttons ')' was clicked
            if (this.value === ")") {
                // If the last string is not +, -, *, /, (
                if (!/[+\-*/(]$/.test(selected_method_input.value)) {
                    const no_of_open_parenthesis = selected_method_input.value.split("(").length - 1;
                    const no_of_close_parenthesis = selected_method_input.value.split(")").length - 1;

                    // If the number of '(' is more than ')'
                    if (no_of_open_parenthesis > no_of_close_parenthesis) {
                        // Add operator
                        selected_method.innerText += " " + this.value;
                        selected_method_input.value += " " + this.value;
                    }
                }
            }
        });
    });

// Auto hide 'Backtest Parameters'
    const long_total = document.getElementById("long_total");
    if (!long_total) {
        document.getElementById("collapse_params_button").click();
    }

// Validate amount from basket trader
    amountInput.addEventListener("keyup", function (event) {
        const value = event.target.value;
        if (value === "" || Number(value) === 0) {
            this.classList.add("is-invalid");
            exportButton.disabled = true;
        } else {
            this.classList.remove("is-invalid");
            validateExportButton();
        }
    });

// Validate file format from basket trader
    fileInput.addEventListener("change", function (event) {
        const value = event.target.value;
        if (!value.endsWith(".csv")) {
            this.classList.add("is-invalid");
            exportButton.disabled = true;
        } else {
            this.classList.remove("is-invalid");
            validateExportButton();
        }
    });

// Validate the export button
    function validateExportButton() {
        exportButton.disabled =
            amountInput.classList.contains("is-invalid") ||
            fileInput.classList.contains("is-invalid") ||
            amountInput.value === ""
    }

// Export button event
    exportButton.addEventListener('click', function () {
        basketTraderModal.hide();
        loadingModal.show();

        // Extract table data
        const table_top_data = extractTableData(document.querySelector("#table_top"));
        const table_bottom_data = extractTableData(document.querySelector("#table_bottom"));

        // Add data to formData
        const formData = new FormData();
        formData.append("file", fileInput.files[0])
        formData.append("table_data", JSON.stringify({
            table_top: table_top_data,
            table_bottom: table_bottom_data,
        }));
        formData.append("amount", amountInput.value);

        // Send request
        fetch("export-csv", {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrf_token,
            },
            body: formData
        })
            .then(response => {
                // Close the basket trader modal
                closeButton.click();

                // Check the response
                if (!response.ok) {
                    console.log(`HTTP error! status: ${response.status}`);
                    messageModalBody.textContent = "Something went wrong! Please try again.";
                    messageModal.show();
                } else if (!response.headers.get('Content-Type').includes('text/csv')) {
                    console.log(`The response is not a CSV file.`);
                    messageModalBody.textContent = "Something went wrong! Please try again.";
                    messageModal.show();
                } else {
                    return response.blob();
                }
            })
            .then(blob => {
                loadingModal.hide();

                // Show important information
                messageModalBody.textContent = "Please carefully read the downloaded basket trader file, IB-TWS may close all irrelevant positions after receiving the file. Please edit the file if necessary.";
                messageModal.show();

                // Download the file
                document.getElementById('messageModal').addEventListener('hidden.bs.modal', function () {
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'basket_trader.csv';
                    a.click();
                });
            });
    })
});


function extractTableData(table) {
    const rows = table.rows;
    const data = [];
    for (let i = 0; i < rows.length; i++) {
        const row = rows[i];
        const rowData = [];
        for (let j = 0; j < row.cells.length; j++) {
            rowData.push(row.cells[j].textContent);
        }
        data.push(rowData);
    }
    return data;
}