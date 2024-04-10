document.addEventListener('DOMContentLoaded', function() {
    var form = document.getElementById('summaryForm');
    var loadingMessage = document.getElementById('loadingMessage');
    var summaryResult = document.getElementById('summaryResult');

    form.addEventListener('submit', function(e) {
        e.preventDefault();
        var formData = new FormData(this);

        // Show loading message
        loadingMessage.style.display = 'block';
        summaryResult.textContent = '';  // Clear previous summary, if any

        fetch('/summary', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (response.headers.get("content-type").includes("application/json")) {
                return response.json();
            } else {
                throw new Error('Non-JSON response received');
            }
        })
        .then(data => {
            loadingMessage.style.display = 'none';  // Hide loading message
            summaryResult.textContent = data.summary;
        })
        .catch(error => {
            console.error('Error:', error);
            loadingMessage.style.display = 'none';  // Hide loading message in case of error
        });
    });
});