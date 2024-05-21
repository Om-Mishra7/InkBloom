function handleImage() {
    const fileInput = document.getElementById('cover');
    const file = fileInput.files[0];

    if (file) {
        const reader = new FileReader();
        reader.onload = function (e) {
            const image = document.getElementById('cover-image');
            image.src = e.target.result;
            image.style.display = 'block';  // Ensure image is displayed
        };
        reader.readAsDataURL(file);
    } else {
        const image = document.getElementById('cover-image');
        image.style.display = 'none';  // Hide image if no file is selected
    }
}


function updateBlog(blogID) {
    const title = document.getElementById('title').value;
    const description = document.getElementById('description').value;
    const slug = document.getElementById('slug').value;
    const tags = document.getElementById('tags').value;
    const category = document.querySelector('input[name="category"]:checked')?.value;
    const visibility = document.querySelector('input[name="visibility"]:checked')?.value;
    const featured = document.getElementById('featured').checked;
    let cover = document.getElementById('cover').files[0];
    const content = quill.getSemanticHTML(0, quill.getLength());

    if (!cover) {
        cover = document.getElementById('cover-image').src;
    }

    if (!title || !description || !slug || !tags || !category || !visibility || !content) {
        createAlert('error', `The following fields are required: ${!title ? 'Title' : ''} ${!description ? 'Description' : ''} ${!slug ? 'Slug' : ''} ${!tags ? 'Tags' : ''} ${!category ? 'Category' : ''} ${!visibility ? 'Visibility' : ''} ${!content ? 'Content' : ''}`);
        return;
    }

    document.getElementById('submit').disabled = true;
    document.getElementById('submit').innerHTML = 'Updating...';

    const formData = new FormData();

    formData.append('title', title);
    formData.append('description', description);
    formData.append('slug', slug);
    formData.append('tags', tags);
    formData.append('category', category);
    formData.append('visibility', visibility);
    formData.append('featured', featured);
    formData.append('cover', cover);
    formData.append('content', content);

    fetch(`/api/blog/${blogID}`, {
        method: 'PUT',
        body: formData,
    })
        .then((response) => response.json())
        .then((data) => {
            if (data.status === 'success') {
                window.location.href = `/blog/${data.slug}`;
            } else {
                createAlert('error', data.message);
                document.getElementById('submit').disabled = false;
                document.getElementById('submit').innerHTML = 'Update Blog';
            }
        })
        .catch((error) => {
            createAlert('error', "Something went wrong. Please try again later.");
            document.getElementById('submit').disabled = false;
            document.getElementById('submit').innerHTML = 'Update Blog';
        });
}


