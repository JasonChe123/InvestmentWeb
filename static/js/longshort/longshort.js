$(document).ready(function () {
    // Useful DOM Element
    const sectorCheckbox = $('.sector-checkbox');
    const amountInput = $('#input-amount');
    const fileInput = $('#file-input')
    const exportButton = $('#export-button');
    const searchField = $('#search-field');
    const searchResult = $('#method-dropdown-menu');
    const selectedMethod = $('#selected-method');
    const selectedMethodInput = $('#selected-method-input');
    const tables = $('table');
    const cells = tables.find('td');
    const basketTraderModal = new bootstrap.Modal($('#basket-trader-modal'));
    const messageModal = new bootstrap.Modal($('#message-modal'));
    const loadingModal = new bootstrap.Modal($('#loading-modal'));
    const csrfToken = $("meta[name='csrf-token']").attr('content');
    const result = $('#longshort-js').attr('result');

    function extractTableData(table) {
        // Return data from given table
        const rows = table.rows;
        const data = [];

        for (let r = 0; r < rows.length; r++) {
            const row = rows[r];
            const rowData = [];
            for (let c = 0; c < row.cells.length; c++) {
                rowData.push(row.cells[c].textContent);
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
        $('.market-cap-checkbox').each(function () {
            if (this.checked) marketCap.push(this.value);
        });
        sectorCheckbox.each(function () {
            if (this.checked) sectors.push(this.value);
        });

        // Request update stock numbers
        $.ajax({
            url: "update-stock-numbers",
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
                $('.sector-checklabel').each(function () {
                    let attr = this.getAttribute('for');
                    if (attr === 'all-sectors-checkbox') {
                        this.innerText = `All (${data.result['All']})`;
                    } else {
                        this.innerText = `${attr} (${data.result[attr]})`;
                    }
                });

                // Update market cap stock numbers
                $('.market-cap-checklabel').each(function () {
                    let attr = this.getAttribute('for');
                    for (let key in data.result) {
                        if (key.includes(attr)) {
                            this.innerText = `${key} (${data.result[key]})`;
                        }
                    }
                });
            },
            error: function (xhr, status, error) {
                console.log("Update stock number error.");
            }
        });
    }

    // Initialize stock number for market cap and sectors
    updateStockNum();

    // 'All' checkbox event
    $('#all-sectors-checkbox').change(function () {
        sectorCheckbox.prop('checked', this.checked);
    });

    // 'Sector' checkbox event
    sectorCheckbox.change(function () {
        const allChecked = sectorCheckbox.length === sectorCheckbox.filter(':checked').length;
        $('#all-sectors-checkbox').prop('checked', allChecked);
        updateStockNum();
    });

    // Start button (show loading modal)
    $('#start-button').click(function () {
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
    $('.market-cap-checkbox').click(function () {
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

        if (value.trim() === "" || value.endsWith('.csv')) {
            this.classList.remove('is-invalid');
            $('#file-input-reset-button').css('right', '1.5rem');
        } else {
            this.classList.add('is-invalid');
            $('#file-input-reset-button').css('right', '3rem');
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
            type: 'POST',
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
                $('#info-message-modal-body').text("Please carefully read the downloaded basket trader file, " +
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

    // Handle messages from server
    function showDynamicMessage(message, type = 'info') {
        // To make sure the consistency to the classes of django messages, please refer to the 
        // templates/_partial/_messages.html
        const container = $(`
            <div class="d-flex mx-1 animate__animated animate__slowest animate__fadeInfadeOut">
                <div class='alert alert-sm alert-${type} mx-0 my-1 px-3 py-1'>
                ${message}
                </div>
            </div>
            `);

        const messagesContainer = $('#messages-container').empty();
        messagesContainer.append(container);
    }

    // Add strategies list
    $('#form-add-strategies-list').on('submit', function (e) {
        e.preventDefault();
        $.ajax({
            url: e.target.action,
            type: e.target.method,
            headers: {
                'X-requested-with': 'XMLHttpRequest',
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
            data: JSON.stringify($(this).serializeArray()),
            success: function (data) {
                if (data.status === "ok") {
                    showDynamicMessage(data.message, 'success');

                    // Update '#add-strategy-message-modal-body'
                    if (data.updated_list && data.updated_list.length > 0) {
                        $('#add-strategy-message-modal-body').empty();

                        // Create Form
                        let newForm = $(`
                        <form id="form-add-strategy-to-list" method="post"
                            action=${$('#add-strategy-message-modal-body').attr('data-url')}>
                            <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken}">
                        </form>
                        `)

                        // Add Checkboxes for Strategies List
                        data.updated_list.forEach(function (item) {
                            const div = $(`
                            <div class="form-check">
                                <div class="mb-3 d-flex">
                                    <input class="form-check-input me-2" type="checkbox" id="checkbox-${item.title}">
                                    <label class="form-check-label flex-grow-1" for="checkbox-${item.title}">${item.title}</label>
                                    <small class="text-secondary">created on: ${item.created_on}</small>
                                </div>
                            </div>
                            `)
                            newForm.append(div);
                        })

                        // Add button
                        let button = $('<button class="btn btn-primary"><i class="bi-plus-circle-fill me-2"></i>Add</button>');
                        newForm.append(button);

                        // Append Form and Show Modal
                        $('#add-strategy-message-modal-body').append(newForm);
                        $('#add-strategy-list-modal').modal('hide');
                        $('#add-strategy-modal').modal('show');
                    }
                }

                // Clear Error Message
                $('#error-message-create-strategies-list').text("");
            },
            error: function (xhr, status, error) {
                // Show Error Message
                $('#error-message-create-strategies-list').text(
                    JSON.parse(xhr.responseText).message
                );
            }
        });
    });

    // Assign Strategy's Param to Add Strategy Modal
    $('.add-strategy').on('click.modal.data-api', function (e) {
        const addStrategyModal = $('#add-strategy-message-modal-body');
        if (addStrategyModal.length === 0) {
            return;
        }
        addStrategyModal.find('input[name="market-cap"]').val($(this).attr('market-cap'));
        addStrategyModal.find('input[name="position-side"]').val($(this).attr('position-side'));
        addStrategyModal.find('input[name="min-stock-price"]').val($(this).attr('min-stock-price'));
        addStrategyModal.find('input[name="sector"]').val($(this).attr('sector'));
        addStrategyModal.find('input[name="formula"]').val($(this).attr('formula'));
        addStrategyModal.find('input[name="sort"]').val($(this).attr('sort'));
    });

    // Validate Chechboxes
    const strategyCheckboxes = $('input[name="strategy-list"]');
    strategyCheckboxes.change(function () {
        strategyCheckboxes.each(function () { this.setCustomValidity('') });
        if (strategyCheckboxes.is(':checked')) {
            strategyCheckboxes.attr('required', false);
        } else {
            strategyCheckboxes.attr('required', true);
        }
    });

    // Add Strategy To List
    $('#form-add-strategy-to-list').on('submit', function (e) {
        e.preventDefault();
        $.ajax({
            url: e.target.action,
            type: e.target.method,
            headers: {
                'X-CSRFToken': csrfToken,
            },
            data: $(this).serialize(),
            success: function (data) {
                showDynamicMessage(data.message);
            },
            error: function (xhr, status, error) {
                showDynamicMessage(data.message, 'error');
                console.log('xhr: ', xhr);
                console.log('status: ', status);
                console.log('error: ', error);
            }
        })
    });
});
