document.addEventListener('DOMContentLoaded', function() {
    // Attach event listener to form submission
    updateProgress();
    var form = document.getElementById('pdf_parser');
    if (form) {
        form.addEventListener('submit', uploadPDF);
    }
    
    // Function to handle PDF upload and get the question
    function uploadPDF(event) {
        event.preventDefault();
        document.getElementById('loader').style.display = 'block'; // Show the spinner

        var formData = new FormData();
        formData.append('pdfFile', document.getElementById('pdfFile').files[0]);
        formData.append('questionType', document.getElementById('questionType').value); // Add the question type to the formData

        fetch('/parse-pdf', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server responded with status ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            document.getElementById('loader').style.display = 'none';
            document.getElementById('generated-question').innerText = data.question;
            document.getElementById('question-section').style.display = 'block';
            attachSubmitAnswerListener(); // Attach listener after the question is loaded
        })
        .catch(error => {
            document.getElementById('loader').style.display = 'none';
            console.error('Error:', error);
            alert('Error: ' + error.message);

            // Display an error message to the user
            });
        
    }
    var showAllBtn = document.getElementById('show-all-btn');
    var showCorrectBtn = document.getElementById('show-correct-btn');
    var showIncorrectBtn = document.getElementById('show-incorrect-btn');

    if (showAllBtn && showCorrectBtn && showIncorrectBtn) {
        showAllBtn.addEventListener('click', function() { filterQuestions('all'); });
        showCorrectBtn.addEventListener('click', function() { filterQuestions('correct'); });
        showIncorrectBtn.addEventListener('click', function() { filterQuestions('incorrect'); });
    }

    // Function to filter questions
    function filterQuestions(filterType) {
        var flashcards = document.querySelectorAll('.flashcard');
        flashcards.forEach(function(card) {
            switch(filterType) {
                case 'correct':
                    card.style.display = card.classList.contains('correct') ? '' : 'none';
                    break;
                case 'incorrect':
                    card.style.display = card.classList.contains('incorrect') ? '' : 'none';
                    break;
                default: // 'all'
                    card.style.display = '';
                    break;
            }
        });
    }

// Function to submit the answer and get the evaluation
    function submitAnswer() {
        var answer = document.getElementById('user-answer').value;
        var question = document.getElementById('generated-question').innerText;

        fetch('/submit-answer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ question: question, answer: answer })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                console.error(data.error);
            } else {
                document.getElementById('evaluation-result').innerText = data.evaluation;
                document.getElementById('evaluation-section').style.display = 'block';
                if (data.is_correct === true) { // Updated condition to check if the answer is correct
                    triggerConfetti(); // Trigger confetti only if the answer is correct
                }
                document.getElementById('new-question-btn').style.display = 'block';
                updateProgress(); // Update progress after submitting the answer
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
    
}



function triggerConfetti() {
    confetti({
        particleCount: 800,
        spread: 100,
        origin: { y: 0.6 }
    });
}
// Function to fetch a new question
function fetchNewQuestion() {
    fetch('/get-new-question')
    .then(response => response.json())
    .then(data => {
        if (data.progress_complete) {
            alert("All questions completed!");
            // Redirect or other actions
        } else {
            document.getElementById('generated-question').innerText = data.question;
            document.getElementById('question-section').style.display = 'block';
            document.getElementById('evaluation-section').style.display = 'none'; // Hide evaluation section
            document.getElementById('user-answer').value = ''; // Reset the answer field
        }
        
    })
    .catch(error => {
        console.error('Error:', error);
        // Display an error message to the user
    });
}

function updateProgress() {
    fetch('/get-progress')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            console.log("Progress data:", data);  // Debugging line
            document.getElementById('total-answered').innerText = data.total_answered;
            document.getElementById('incorrect-answers').innerText = data.incorrect_answers;
        })
        .catch(error => {
            console.error('Error:', error);
        });
}


// Function to attach event listener to submit answer button
function attachSubmitAnswerListener() {
    var submitBtn = document.getElementById('submit-answer-btn');
    if (submitBtn) {
        submitBtn.addEventListener('click', submitAnswer);
    }
}

// Function to attach event listener to new question button
function attachNewQuestionListener() {
    var newQuestionBtn = document.getElementById('new-question-btn');
    if (newQuestionBtn) {
        newQuestionBtn.addEventListener('click', fetchNewQuestion);
        }
}
// Initially attach listeners to elements that are available on page load
attachSubmitAnswerListener(); // For submit answer button
attachNewQuestionListener(); // For new question button
});
