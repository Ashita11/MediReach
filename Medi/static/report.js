document.getElementById('details-form').addEventListener('submit', function(event) {
    event.preventDefault();
    const fileInput = document.getElementById('pdf-file');
    const file = fileInput.files[0];

    const age = document.getElementById('age').value;
    const weight = document.getElementById('weight').value;
    const height = document.getElementById('height').value;
    const activityLevel = document.getElementById('activity-level').value;
    if (file) {
        const formData = new FormData();
        formData.append('file', file);

        // Example API call to analyze the PDF and get diet recommendations
        fetch('https://api.example.com/analyzeReport', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            const output = document.getElementById('recommendation-output');
            output.innerHTML = `<p>${data.recommendation}</p>`;
        })
        .catch(error => {
            console.error('Error:', error);
        });
    } else {
        alert('Please upload a PDF file.');
    }
});
    // Example API call to get diet recommendations
    fetch('https://api.example.com/getDietRecommendations', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ age, weight, height, activityLevel })
    })
    .then(response => response.json())
    .then(data => {
        const output = document.getElementById('recommendation-output');
        output.innerHTML = `<p>${data.recommendation}</p>`;
    })
    .catch(error => {
        console.error('Error:', error);
    });
