function renderStatisticsChart(correctAnswers, incorrectAnswers) {
    var ctx = document.getElementById('statisticsChart').getContext('2d');
    var chart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: ['Correct Answers', 'Incorrect Answers'],
            datasets: [{
                data: [correctAnswers, incorrectAnswers],
                backgroundColor: [
                    'rgba(54, 162, 235, 0.2)',
                    'rgba(255, 99, 132, 0.2)'
                ],
                borderColor: [
                    'rgba(54, 162, 235, 1)',
                    'rgba(255, 99, 132, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 3,
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: true,
                    text: 'Quiz Performance'
                }
            }
        }
    });
    
}

// Ensure this function gets called with the correct data
document.addEventListener('DOMContentLoaded', function() {
    renderStatisticsChart(correctAnswers, incorrectAnswers);

});
