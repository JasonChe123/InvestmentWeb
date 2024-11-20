document.addEventListener('DOMContentLoaded', function () {
    // Add selected method
    function addSelectedMethod(method) {
        const selected_method = document.getElementById("selected_method");
        const selected_method_input = document.getElementById("selected_method_input");

        // If the last string is +, -, *, /, (
        if (/[\+\-\*\/(]$/.test(selected_method.innerText)) {
            // Add the selected method
            selected_method.innerText += " " + method;
            selected_method_input.value += " " + method;
        }
        // If the string includes +, -, *, /
        else if (/[\+\-\*\/]/.test(selected_method.innerText)) {
            // If +, -, *, / and followed by not(+, -, *, /)
            const lastOperatorIndex = selected_method.innerText.search(/[\+\-\*\/][^+\-*/]*$/);
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

    // Toggle show/ hide text in collapse button
    var collapse_params_button = document.getElementById('collapse_params_button');
    var backtest_params_area = document.getElementById('backtest_params_area');
    backtest_params_area.addEventListener('show.bs.collapse', function () {
        collapse_params_button.innerText = "Hide";
    });
    backtest_params_area.addEventListener('hidden.bs.collapse', function () {
        collapse_params_button.innerText = "Show";
    });

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
});