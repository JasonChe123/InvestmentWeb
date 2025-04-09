$(document).ready(function () {
    // DOM element
    const allCheckbox = $('#all-sectors-checkbox');
    const marketCapCheckbox = $('.market-cap-checkbox');
    const marketCapCheckLabel = $('.market-cap-checklabel');
    const sectorCheckbox = $('.sector-checkbox');
    const sectorCheckLabel = $('.sector-checklabel');
    const startButton = $('#start-button');
    const amountInput = $('#input-amount');
    const fileInput = $('#file-input')
    const exportButton = $('#export-button');
    const basketTraderModal = new bootstrap.Modal($('#basket-trader-modal'));
    const messageModal = new bootstrap.Modal($('#message-modal'));
    const messageModalBody = $('#message-modal-body');
    const loadingModal = new bootstrap.Modal($('#loading-modal'));
    const searchField = $('#search-field');
    const searchResult = $('#method-dropdown-menu');
    const selectedMethod = $('#selected-method');
    const selectedMethodInput = $('#selected-method-input');
    const tables = $('table');
    const cells = tables.find('td');

    // CSRF token
    const scriptTag = $('#longshort-js');
    const csrfToken = scriptTag.attr("csrf_token");

    // For collapse/ expand the backtest parameters
    const result = scriptTag.attr("result");

    function extractTableData(table) {
        /* Return data from table. */
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
        if (method.includes("...")) {
            return;
        }
        /* Modify the 'Selected Method' from input-params. */
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
        /* Validate the export button with amount input and file type checking. */
        let amountInvalid = amountInput.hasClass("is-invalid") || !amountInput.val();
        let fileTypeInvalid = fileInput.hasClass("is-invalid");
        exportButton.prop('disabled', amountInvalid || fileTypeInvalid);
    }

    function updateStockNum() {
        /* Update the stock number for each sector and market-cap. */
        // Get selected market cap and sectors
        let marketCap = [];
        let sectors = [];
        marketCapCheckbox.each(function () {
            if (this.checked) marketCap.push(this.value);
        });
        sectorCheckbox.each(function () {
            if (this.checked) sectors.push(this.value);
        });

        // Request update stock numbers
        $.ajax({
            url: 'update-stock-numbers',
            type: 'POST',
            headers: {
                'X-requested-with': 'XMLHttpRequest',
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
            data: JSON.stringify({
                'market_cap': marketCap,
                'sectors': sectors,
            }),
            success: function (data) {
                // Update sectors stock numbers
                sectorCheckLabel.each(function () {
                    let attr = this.getAttribute('for');
                    if (attr === 'all-sectors-checkbox') {
                        this.innerText = `All (${data.result['All']})`;
                    } else {
                        this.innerText = `${attr} (${data.result[attr]})`;
                    }
                });

                // Update market cap stock numbers
                marketCapCheckLabel.each(function () {
                    let attr = this.getAttribute('for');
                    for (let key in data.result) {
                        if (key.includes(attr)) {
                            this.innerText = `${key} (${data.result[key]})`;
                        }
                    }
                });
            },
            error: function (xhr, status, error) {
                console.log("message from server: ", xhr.responseText);
            }
        })
    }

    // Initialize stock number for market cap and sectors
    updateStockNum();

    // 'All' checkbox event
    allCheckbox.change(function () {
        sectorCheckbox.prop('checked', this.checked);
    });

    // 'Sector' checkbox event
    sectorCheckbox.change(function () {
        const allChecked = sectorCheckbox.length === sectorCheckbox.filter(':checked').length;
        allCheckbox.prop('checked', allChecked);
        updateStockNum();
    });

    // Amount input event
    amountInput.change(validateExportButton);

    // File input event
    fileInput.change(validateExportButton);

    // Start button (show loading modal)
    startButton.click(function () {
        loadingModal.show();
        // Server will render the page with the calculated result
    });

    // Format table: 'red' color for negative values, align all numbers to the right, turn numbers to scientific notation
    for (let i = 0; i < cells.length; i++) {
        const value = parseFloat(cells[i].textContent);
        if (typeof (value) === 'number' && !isNaN(value)) cells[i].style.textAlign = 'right';
        if (!isNaN(value) && value < 0) cells[i].classList.add("text-danger");
        if (!cells[i].classList.contains("summary")) {
            if (value > 1000 || value < -1000) cells[i].textContent = value.toExponential(2);
        }
    }

    // Format table (.table-top.table-bottom): add left border to ticker columns (header rows)
    const dataTables = $('.table-top,.table-bottom');
    const dataTableheads = dataTables.find('th');
    const dataTableCells = dataTables.find('td');
    for (let i = 0; i < dataTableheads.length; i++) {
        if (dataTableheads[i].cellIndex % 3 === 0) {
            dataTableheads[i].classList.add('border-start');
            dataTableheads[i].classList.add('border-primary');
        }
    }

    // Format table: add left border to ticker columns (data rows)
    for (let j = 0; j < dataTableCells.length; j++) {
        if (dataTableCells[j].cellIndex % 3 === 0) {
            dataTableCells[j].classList.add('border-start');
            dataTableCells[j].classList.add('border-primary');
        }
    }

    // Re-toggle dropdown-menu (colapse it)
    searchField.on("click", function (e) {
        searchField.dropdown("toggle");
    });

    // Search-method event
    searchField.keyup(function (event) {
        // Arrow-key-down -> navigate dropdown-menu
        if (event.keyCode === 40) {
            if (searchResult.find("a").length > 0) {
                searchResult.show();
                searchResult.find("a")[0].focus();
                return;
            }
        }

        // Ajax: search report data names
        const search_value = event.target.value;
        $.ajax({
            url: 'search-method',
            type: 'POST',
            headers: {
                "X-requested-with": "XMLHttpRequest",
                "Content-Type": "application/json",
                'X-CSRFToken': csrfToken,
            },
            data: JSON.stringify({ "search_text": search_value }),
            success: function (data) {
                // Reset result
                searchResult.empty();

                if (data.result.length > 0) {
                    // Add results
                    for (let i = 0; i < data.result.length; i++) {
                        // Create dropdown-item
                        let link = $('<li><a class="dropdown-item" href="#"></a></li>');
                        link.find("a").text(data.result[i]);
                        searchResult.append(link);

                        // Click event -> add to "Selected Method"
                        link.find("a").click(function () {
                            modifySelectedMethod(data.result[i]);

                            // Initialize the search field
                            searchResult.empty();
                            searchResult.hide();
                            searchField.val("");
                            searchField.focus();
                        });
                    }
                    searchResult.show()
                } else {
                    searchResult.hide()
                }
            },
            error: function (xhr, status, error) {
                searchResult.empty();
                searchResult.hide();
            }
        })
    });

    // Ajax: update stock numbers
    marketCapCheckbox.click(function () {
        updateStockNum();
    });

    // Modify 'Selected Method' from dropdown
    $('.method-selector').change(function () {
        modifySelectedMethod(this.value);
    });

    // Math operator event
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

    // Auto expand 'Backtest Parameters'
    if (!result) {
        $('#collapse-params-button').click();
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

        // Validate table data
        const longTables = $('.table-top');
        if (longTables.length === 0) {
            return;
        }

        // Extract table data
        let longTableData = [];
        for (let i = 0; i < longTables.length; i++) {
            longTableData.push(extractTableData(longTables[i]));
        }

        const shortTables = $('.table-bottom');
        let shortTableData = [];
        for (let i = 0; i < shortTables.length; i++) {
            shortTableData.push(extractTableData(shortTables[i]));
        }

        // Add data to formData
        const formData = new FormData();
        formData.append("file", fileInput[0].files[0])
        formData.append("table_data", JSON.stringify({
            long_table: longTableData,
            short_table: shortTableData,
        }));
        formData.append("amount", amountInput.val());

        // Send request
        loadingModal.show();
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
                setTimeout(function () {
                    loadingModal.hide()
                }, 500);

                // Show important information
                messageModalBody.text("Please carefully read the downloaded basket trader file, " +
                    "IB-TWS may close all irrelevant positions after receiving the file. Please edit the " +
                    "file if necessary.");
                messageModal.show();

                // Download the file
                const blob = new Blob([response], { type: 'text/csv' });
                $('#message-modal').on('hidden.bs.modal', function () {
                    const url = window.URL.createObjectURL(blob);
                    $(`<a href="${url}" hidden download="basket_trader.csv"></a>`)[0].click()
                });
            },
            error: function (xhr, status, error) {
                setTimeout(function () {
                    loadingModal.hide();
                }, 500);
            }
        });
    })

    // Message (from server) handling for AJAX responses
    function showDynamicMessage(message, type = 'info') {
        // Create messages container if it doesn't exist
        let messagesContainer = document.querySelector('.messages');
        if (!messagesContainer) {
            messagesContainer = document.createElement('div');
            messagesContainer.className = 'messages';
            document.querySelector('main').prepend(messagesContainer);
        }

        // Create message element
        const messageElement = document.createElement('div');
        messageElement.className = `alert alert-sm alert-${type}`;
        messageElement.textContent = message;

        // Add to container
        messagesContainer.appendChild(messageElement);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            messageElement.remove();
            if (messagesContainer.children.length === 0) {
                messagesContainer.remove();
            }
        }, 5000);
    }

    // Button click handler (My Strategy Button), send ajax request to update database
    $('.my-strategy').click(function (e) {
        // Get button values
        let action = e.target.value.split(',')[0].trim();
        let sector = e.target.value.split(',')[1].trim();

        // Send AJAX request
        $.ajax({
            url: 'alter-my-strategy',
            type: 'POST',
            headers: {
                'X-requested-with': 'XMLHttpRequest',
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
            data: JSON.stringify({
                "action": action,
                "market_cap": scriptTag.attr("market_cap"),
                "pos_hold": scriptTag.attr("pos_hold"),
                "min_stock_price": scriptTag.attr("min_stock_price"),
                "sorting_method": scriptTag.attr("sorting_method"),
                "sector": sector,
                "formula": scriptTag.attr("formula"),
            }),
            success: function (data) {
                if (data.message) {
                    showDynamicMessage(data.message, data.message_type || 'info');
                    // Toggle button text, value and classes
                    const button = $(e.target);
                    if (action === 'add') {
                        button.text('Delete')
                            .val('delete,' + sector)
                            .removeClass('btn-primary')
                            .addClass('btn-danger');
                    } else {
                        button.text('Add')
                            .val('add,' + sector)
                            .removeClass('btn-danger')
                            .addClass('btn-primary');
                    }
                }
            },
            error: function (xhr, status, error) {
                let message = JSON.parse(xhr.responseText).message;
                showDynamicMessage(message, 'danger');
            }
        });
    });
});
