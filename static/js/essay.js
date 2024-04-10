$(document).ready(function() {
    $('#toggle-essay-btn').click(function() {
        $('#original-essay').toggle();
    });
});
$(document).ready(function() {
    $('#essayForm').on('submit', function(e) {
        e.preventDefault();

        // Form Validation
        var fileInput = $('#essayFile')[0];
        if (fileInput.files.length === 0) {
            alert('Please select a file to upload.');
            return;
        }

        // Show loading indicator
        $('#loadingIndicator').removeClass('hidden');

        // AJAX Form Submission
        var formData = new FormData(this);
        $.ajax({
            url: '/upload-essay',
            type: 'POST',
            data: formData,
            contentType: false,
            processData: false,
            success: function(response) {
                // Hide loading indicator
                $('#loadingIndicator').addClass('hidden');

                // Display feedback
                $('body').html(response);
            },
            error: function() {
                alert('There was an error processing your essay.');
                $('#loadingIndicator').addClass('hidden');
            }
        });
    });
});