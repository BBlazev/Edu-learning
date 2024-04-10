function uploadFile() {
    var fileInput = document.getElementById('fileInput');
    var file = fileInput.files[0];

    if (!file) {
        alert('Please select a file to upload');
        return;
    }

    var formData = new FormData();
    formData.append('file', file);

    var xhr = new XMLHttpRequest();
    xhr.open('POST', 'http://127.0.0.1:5000/upload-audio', true); // Updated URL

    xhr.upload.onprogress = function(e) {
        if (e.lengthComputable) {
            var percentComplete = Math.round((e.loaded / e.total) * 100);
            var progressBar = document.getElementById('progressBar');
            progressBar.style.width = percentComplete + '%';
            progressBar.textContent = percentComplete + '%';
        }
    };

    xhr.onload = function() {
        if (xhr.status === 200) {
            document.getElementById('uploadStatus').innerText = 'Upload Complete: ' + xhr.responseText;
        } else {
            document.getElementById('uploadStatus').innerText = 'Upload failed';
        }
    };

    xhr.send(formData);
}