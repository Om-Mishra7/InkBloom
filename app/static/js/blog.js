hljs.highlightAll();

function submitComment(blogID) {
    let commentContent = document.getElementById('comment-content').value;

    if (commentContent === '') {
        createAlert('danger', 'Please ensure that your comment is not empty, and try again.');
        return;
    }

    let formData = new FormData();
    formData.append('content', commentContent);

    fetch(`/api/blog/${blogID}/comment`, {
        method: 'POST',
        body: formData,
    }).then(response => {
        if (response.status === 200) {
            createAlert('success', 'Comment saved successfully, refreshing page...');
            document.getElementById('comment-content').value = '';
            setTimeout(() => {
                location.reload();
            }, 1000);
        } else {
            createAlert('danger', 'An error occurred while submitting your comment. Please try again.');
        }
    }).catch(error => {
        createAlert('danger', 'An error occurred while submitting your comment. Please try again.');
    }
    );
}
