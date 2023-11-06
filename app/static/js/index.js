// Load more blogs when user scrolls to the middle of the page


document.addEventListener('DOMContentLoaded', () => {
    // Load more blogs when user scrolls to the middle of the page
    window.onscroll = () => {
        if (window.innerHeight + window.scrollY >= document.body.offsetHeight / 2) {
            load_more();
        }
    };
}
);

// Load more blogs

function load_more() {
    lastBlogID = document.querySelector('.blog:last-child').getAttribute('data-id');
    
    fetch(`/api/v1/blogs/${lastBlogID}`)
    .then(response => response.json())
    .then(data => {
        data.forEach(add_blog_to_dom);
    })
    .catch(error => console.log(error));
}