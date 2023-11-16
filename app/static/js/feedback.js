let feedbackForm = document.getElementById('feedback-form');
feedbackForm.addEventListener('submit', function (e) {
    e.preventDefault();
    let feedback = document.getElementById('feedback').value;
    let csrfToken = document.getElementById('csrf_token').value;
    fetch('/api/v1/feedback', {
        method: 'POST',
        body: JSON.stringify(
            {
                feedback: feedback,
                csrf_token: csrfToken
            }
        ),
        headers: {
            'Content-Type': 'application/json'
        }
    }).then((res) => res.json())
        .then((data) => {
            if (data.status == "success") {
                createAlert("success", data.message.replace(/\s/g , '-').trim());
                setTimeout(() => {
                    window.location.href = '/';
                }
                    , 1000);
            } else {
                    createAlert("alert", data.message.replace(/\s/g , '-').trim());
            }
        })
        .catch((err) => console.log(err));
}
);
