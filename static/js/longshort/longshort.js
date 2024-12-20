$(document).ready(function () {
    // Elements
    const startButton = $('#start-button');
    const amountInput = $('#input-amount');
    const fileInput = $('#file-input')
    const exportButton = $('#export-button');
    const basketTraderModal = new bootstrap.Modal($('#basket-trader-modal'));
    const messageModal = new bootstrap.Modal($('#message-modal'));
    const messageModalBody = $('#message-modal-body');
    const loadingModal = new bootstrap.Modal($('#loading-modal'));
    const searchField = $('#search-field');
    const searchResult = $('#search-result');
    const selectedMethod = $('#selected-method');
    const selectedMethodInput = $('#selected-method-input');
    const longTotal = $('#long-total');
    const tables = $('table');
    const heads = $('th');
    const cells = $('td');

    // CSRF token
    const scriptTag = $('#longshort-js');
    const csrfToken = scriptTag.attr("csrf_token");

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

    function modifySelectedMethod(method) {
        // If the last string is +, -, *, /, (
        if (/[+\-*\/(]$/.test(selectedMethod.text())) {
            // Add the selected method
            selectedMethod.text(selectedMethod.text() + " " + method);
            selectedMethodInput.val(selectedMethodInput.val() + " " + method);
        }
        // If the string includes +, -, *, /
        else if (/[+\-*\/]/.test(selectedMethod.text())) {
            // If +, -, *, / and followed by not(+, -, *, /)
            const lastOperatorIndex = selectedMethod.text().search(/[+\-*\/][^+\-*/]*$/);
            if (lastOperatorIndex !== -1) {
                // Replace the last method string
                const newString = selectedMethod.text().slice(0, lastOperatorIndex + 2) + method;
                selectedMethod.text(newString);
                selectedMethodInput.val(newString);
            }
        }
        // Else
        else {
            selectedMethod.text(method);
            selectedMethodInput.val(method);
        }
    }

    function validateExportButton() {
        let amountInvalid = amountInput.hasClass("is-invalid") || !amountInput.val();
        let fileTypeInvalid = fileInput.hasClass("is-invalid");
        exportButton.prop('disabled', amountInvalid || fileTypeInvalid);
    }

    searchResult.hide();

    // Start button (show loading modal)
    startButton.click(function () {
        loadingModal.show();
        // Server will render the page with the calculated result
    });

    // Format table: 'red' color for negative values, align all numbers to the right
    for (let i = 0; i < cells.length; i++) {
        const value = parseFloat(cells[i].textContent);
        if (typeof (value) === 'number' && !isNaN(value)) cells[i].style.textAlign = 'right';
        if (!isNaN(value) && value < 0) cells[i].style.color = 'red';
    }

    // Format table: add border to all tables
    for (let i = 0; i < tables.length; i++) {
        tables[i].style.border = '1px solid #bbb';
    }

    // Format table: add left border to all ticker columns
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

    // POST request: search for backtest parameters
    searchField.keyup(function (event) {
        const search_value = event.target.value;
        $.ajax({
            url: 'search-method',
            type: 'POST',
            headers: {
                "X-requested-with": "XMLHttpRequest",
                "Content-Type": "application/json",
                'X-CSRFToken': csrfToken,
            },
            data: JSON.stringify({"search_text": search_value}),
            success: function (data) {
                searchResult.text("");
                if (data.result.length > 0) {
                    searchResult.show();

                    // Add results
                    for (let i = 0; i < data.result.length; i++) {
                        const link = $('<a class="dropdown-item"></a>').text(data.result[i]);
                        searchResult.append(link);

                        // Add to "Selected Method"
                        link.click(function () {
                            modifySelectedMethod(data.result[i]);

                            // Initialize the search field
                            searchField.val("");
                            searchResult.text("");
                            searchResult.hide();
                        });
                    }
                } else {
                    searchResult.hide();
                }
            },
            error: function (xhr, status, error) {
                searchResult.text("");
                searchResult.hide();
            }
        })
    });

    // Modify 'Selected Method' from dropdown
    $('.method-selector').change(function () {
        modifySelectedMethod(this.value);
    });

    // Operator event
    $('.operator').each(function (e) {
        $(this).click(function () {
            // If the AC button was clicked
            if (this.value === "AC") {
                selectedMethod.text("Please select a method...");
                selectedMethodInput.val("");
                return;
            }

            // If buttons +, -, *, / were clicked
            if (/[+\-*/]/.test(this.value)) {
                // If the selected method is empty
                if (selectedMethodInput.val() === "") return;

                // If the last string is '('
                if (/[(]$/.test(selectedMethodInput.val())) return;

                // If the last string is +, -, *, /
                if (/[+\-*/]$/.test(selectedMethodInput.val())) {
                    // Replace the last operator
                    selectedMethod.text(selectedMethod.text().slice(0, -1) + this.value);
                    selectedMethodInput.val(selectedMethodInput.val().slice(0, -1) + this.value);
                    return;
                }

                // Add operator
                selectedMethod.text(selectedMethod.text() + " " + this.value);
                selectedMethodInput.val(selectedMethodInput.val() + " " + this.value);
                return;
            }

            // If buttons '(' was clicked
            if (this.value === "(") {
                // If the selected method is empty
                if (selectedMethodInput.val() === "") {
                    // Add operator
                    selectedMethod.text(this.value);
                    selectedMethodInput.val(this.value);
                }

                // If the last string is +, -, *, /
                else if (/[+\-*/]$/.test(selectedMethodInput.val())) {
                    // Add operator
                    selectedMethod.text(selectedMethod.text() + " " + this.value);
                    selectedMethodInput.val(selectedMethodInput.val() + " " + this.value);
                }
            }

            // If buttons ')' was clicked
            if (this.value === ")") {
                // If the last string is not +, -, *, /, (
                if (!/[+\-*/(]$/.test(selectedMethodInput.val())) {
                    const no_of_open_parenthesis = selectedMethodInput.val().split("(").length - 1;
                    const no_of_close_parenthesis = selectedMethodInput.val().split(")").length - 1;

                    // If the number of '(' is more than ')'
                    if (no_of_open_parenthesis > no_of_close_parenthesis) {
                        // Add operator
                        selectedMethod.text(selectedMethod.text() + " " + this.value);
                        selectedMethodInput.val(selectedMethodInput.val() + " " + this.value);
                    }
                }
            }
        });
    });

    // Auto show 'Backtest Parameters'
    if (longTotal.length === 0) {
        $('#collapse_params_button').click();
    }

    // Validate amount from basket trader
    amountInput.on("input change blur", function (event) {
        const value = event.target.value.trim();
        if (value === "" || Number(value) <= 0) {
            this.classList.add("is-invalid");
            exportButton.prop('disable', true);
        } else {
            this.classList.remove("is-invalid");
        }
        validateExportButton();
    });

    // Validate file format from basket trader
    fileInput.change(function (event) {
        const value = event.target.value;
        if (!value.endsWith(".csv")) {
            this.classList.add("is-invalid");
            exportButton.prop("disabled", true);
        } else {
            this.classList.remove("is-invalid");
        }
        validateExportButton();
    });

    // Export basket trader
    exportButton.click(function () {
        basketTraderModal.hide();
        loadingModal.show();

        // Extract table data
        const longTableData = extractTableData($('#table-top')[0]);
        const shortTableData = extractTableData($('#table-bottom')[0]);

        // Add data to formData
        const formData = new FormData();
        formData.append("file", fileInput[0].files[0])
        formData.append("table_data", JSON.stringify({
            long_table: longTableData,
            short_table: shortTableData,
        }));
        formData.append("amount", amountInput.val());

        // Send request
        $.ajax({
            url: 'export-csv',
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
            },
            data: formData,
            processData: false,
            contentType: false,
            success: function (response) {
                loadingModal.hide();

                // Show important information
                messageModalBody.text("Please carefully read the downloaded basket trader file, " +
                    "IB-TWS may close all irrelevant positions after receiving the file. Please edit the " +
                    "file if necessary.");
                messageModal.show();

                // Download the file
                const blob = new Blob([response], {type: 'text/csv'});
                $('#message-modal').on('hidden.bs.modal', function () {
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'basket_trader.csv';
                    a.click();
                });
            },
            error: function (xhr, status, error) {
                setTimeout(function () {
                    loadingModal.hide();
                }, 500);
            }
        });
    })
});