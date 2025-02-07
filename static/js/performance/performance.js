$(document).ready(function () {
    // Get Elements
    const loadingModal = new bootstrap.Modal($('#loading-modal'));
    const backButton = $('#back-btn');
    const portfolioNameInput = $('#input-portfolio-name');
    const fileInput = $('#input-file');
    const applyButton = $('#button-apply');
    const portfolioNameError = $('#portfolio-name-error');
    const fileTypeError = $('#file-type-error');
    const uploadButton = $('#button-upload');
    const tables = $('table');
    const heads = tables.find('th');
    const cells = tables.find('td');

    // Variables from script-tag
    const scriptTag = $('#performance-js');
    const csrfToken = scriptTag.attr('csrf_token');


    // Other variables
    let portfolioToDelete = null;
    let portfolioToEdit = null;
    let portfolioNameValid = true;
    let fileTypeValid = true;

    function checkPortfolioName(input) {
        if (input.value.trim()) {
            $.ajax({
                url: "check_portfolio_name",
                type: "POST",
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': csrfToken,
                },
                data: {
                    portfolio_name: input.value.trim(),
                },
                success: function (response) {
                    // If portfolio exists
                    if (response.exists) {
                        validatePortfolioName(false);
                    } else {
                        validatePortfolioName(true);
                    }
                    validateForm();
                },
                error: function (xhr, status, error) {
                    validatePortfolioName(false);
                    console.error("Error checking portfolio name.");
                    validateForm();
                }
            });

        } else {
            validatePortfolioName(true)
            validateForm();
        }
    }

    function validatePortfolioName(flag) {
        if (flag) portfolioNameError.hide(); else portfolioNameError.show();
        portfolioNameValid = flag;
    }

    function validateFileType(flag) {
        if (flag) fileTypeError.hide(); else fileTypeError.show();
        fileTypeValid = flag;
    }

    function validateForm() {
        if (portfolioNameInput[0].value.trim() === "" && fileInput[0].files.length === 0) {
            applyButton.prop('disabled', true);
        } else {
            if (!portfolioNameValid || !fileTypeValid) {
                applyButton.prop('disabled', true);
            } else {
                applyButton.prop('disabled', false);
            }
        }
        // For 'add_portfolio' page
        if (!portfolioNameValid || !fileTypeValid) {
            uploadButton.prop('disabled', true);
        } else {
            uploadButton.prop('disabled', false);
        }
    }

    // Format table, red color for negative
    for (let i = 0; i < cells.length; i++) {
        const value = parseFloat(cells[i].textContent);
        if (!isNaN(value) && value < 0) {
            cells[i].classList.add("text-danger");
            cells[i].textContent = `( ${cells[i].textContent.replace("-", "")} )`;
        }
    }

    // Format total_performance
    const totalPerf = $(".total-performance");
    totalPerf.text(function(_, orgText){
        if (parseFloat(orgText) < 0) {
            return `( ${orgText.replace("-", "")} % )`
        } else {
            return `+ ${orgText} %`
        }
    });

    // Back button
    backButton.click(function () {
        window.history.back();
    })

    // Delete buttons
    $('button[name="delete"]').each(function () {
        $(this).click(function () {
            portfolioToDelete = $(this).val();

            // Show confirmation modal
            $('#confirmation-modal').modal('show');
        });
    });

    // Confirm delete button
    $('#confirm-delete').click(function () {
        if (portfolioToDelete) {
            $('#confirmation-modal').modal('hide');
            loadingModal.show();
            $.ajax({
                url: "delete_portfolio",
                type: "POST",
                data: JSON.stringify({
                    portfolio_name: portfolioToDelete
                }),
                contentType: "application/json",
                dataType: "json",
                headers: {
                    "X-CSRFToken": csrfToken
                },
                success: function (response) {
                    if (response.status === "success") {
                        location.reload();
                    } else {
                        alert("Error deleting portfolio: " + response.message);
                        loadingModal.hide();
                    }
                },
                error: function (xhr, status, error) {
                    alert("An error occurred while deleting the portfolio.");
                    setTimeout(function () {
                        loadingModal.hide();
                    }, 500);
                }
            });
        }
    });

    // Edit buttons
    $('button[name="edit"]').each(function () {
        $(this).click(function () {
            portfolioToEdit = this.value;

            // Reset elements
            portfolioNameInput[0].value = "";
            portfolioNameError.hide();
            applyButton[0].disabled = true;

            // Show confirmation modal
            $('#edit-portfolio-modal').modal('show');
        });
    });

    // Apply button
    applyButton.click(function () {
        var formData = new FormData();

        // Add file and portfolio_name
        if (fileInput[0].files.length > 0) {
            formData.append('portfolio_file', fileInput[0].files[0]);
        } else {
            formData.append('portfolio_file', "");
        }
        formData.append('portfolio_name', portfolioToEdit);
        formData.append('new_portfolio_name', portfolioNameInput[0].value);

        // POST request
        $('#edit-portfolio-modal').modal('hide');
        loadingModal.show();
        $.ajax({
            url: "edit_portfolio",
            type: "POST",
            headers: {
                "X-CSRFToken": csrfToken
            },
            data: formData,
            processData: false,
            contentType: false,
            success: function (response) {
                location.reload();
            },
            error: function (xhr, status, error) {
                console.error("Error editing portfolio: ", error);
                alert("An error occurred while editing the portfolio.");
                setTimeout(function () {
                    location.reload();
                }, 500);

            }
        });
    });

    // Validate portfolio name
    portfolioNameInput.on('input change blur', function () {
        checkPortfolioName(this);
    });

    // Validate file type
    fileInput.change(function (event) {
        if (event.target.files.length > 0) {
            let fileType = event.target.files[0].type;
            if (fileType === "text/csv") validateFileType(true); else validateFileType(false);
        } else {
            validateFileType(true);
        }
        validateForm();
    });
});