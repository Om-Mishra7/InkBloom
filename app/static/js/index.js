function load_more() {
  if (window.innerHeight + window.scrollY >= document.body.offsetHeight) {
    lastBlogID = document
      .querySelector(".blog:last-child")
      .getAttribute("data-id");

    // Remove the scroll event listener before making the fetch request
    window.removeEventListener("scroll", load_more);

    fetch(`/api/v1/blogs/${lastBlogID}`)
      .then((response) => {
        if (response.status == 404) {
          // If the response is 404, there are no more blogs to load
          return Promise.reject("No more blogs to load");
        }
        return response.json();
      })
      .then((data) => {
        data.forEach(add_blog);
        // Add the scroll event listener back after loading more
        window.addEventListener("scroll", load_more);
      })
      .catch((error) => {
        // Handle the "No more blogs to load" error here, e.g., show a message to the user
        console.log(error);
      });
  }
}

window.addEventListener("scroll", load_more);
