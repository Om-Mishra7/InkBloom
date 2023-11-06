function capitalizeFirstLetter(string) {
  return string.charAt(0).toUpperCase() + string.slice(1);
}

function load_more() {

  if (window.innerHeight + window.scrollY >= document.body.offsetHeight / 2) {
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
        console.log(error);
      });
  }
}

function add_blog(blog) {
  let blogHTML = `<div class="blog" data-id=${blog._id}>
    <div class="blog-details">
      <div class="blog-metadata">
        <p class="author-image">
          <img
            src=${blog.authour_profile_pic}
          />
        </p>
        <p class="author-name">${blog.authour_name}</p>
        <p class="blog-publish-date">${blog.created_at}</p>
      </div>

      <div class="blog-main-section">
        <a
          class="blog-link"
          href="/blogs/${blog.slug}"
        >
          <div class="blog-title">
            <h1>
                ${blog.title}
            </h1>
          </div>

          <div class="blog-summary">
            <p>
                ${blog.summary}...
            </p>
          </div>
        </a>
      </div>

      <div class="blog-footer">
        "BLOG TAGS"
        <div class="read-time">
          <p>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              height="24"
              viewBox="0 -960 960 960"
              width="24"
            >
              <path
                d="m612-292 56-56-148-148v-184h-80v216l172 172ZM480-80q-83 0-156-31.5T197-197q-54-54-85.5-127T80-480q0-83 31.5-156T197-763q54-54 127-85.5T480-880q83 0 156 31.5T763-763q54 54 85.5 127T880-480q0 83-31.5 156T763-197q-54 54-127 85.5T480-80Zm0-400Zm0 320q133 0 226.5-93.5T800-480q0-133-93.5-226.5T480-800q-133 0-226.5 93.5T160-480q0 133 93.5 226.5T480-160Z"
              /></svg
            >${blog.read_time}
          </p>
        </div>

        <div class="blog-views">
          <p>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              height="24"
              viewBox="0 -960 960 960"
              width="24"
            >
              <path
                d="M480-320q75 0 127.5-52.5T660-500q0-75-52.5-127.5T480-680q-75 0-127.5 52.5T300-500q0 75 52.5 127.5T480-320Zm0-72q-45 0-76.5-31.5T372-500q0-45 31.5-76.5T480-608q45 0 76.5 31.5T588-500q0 45-31.5 76.5T480-392Zm0 192q-146 0-266-81.5T40-500q54-137 174-218.5T480-800q146 0 266 81.5T920-500q-54 137-174 218.5T480-200Zm0-300Zm0 220q113 0 207.5-59.5T832-500q-50-101-144.5-160.5T480-720q-113 0-207.5 59.5T128-500q50 101 144.5 160.5T480-280Z"
              />
            </svg>
            ${blog.views}
          </p>
        </div>
      </div>
    </div>
    <div class="blog-image">
      <img
        src=${blog.cover_image}
      />
    </div>
  </div>`;

  tagDiv = document.createElement("div");
  tagDiv.classList.add("blog-tags");
  blog.tags.forEach((tag) => {
    tagDiv.innerHTML += `<p>${capitalizeFirstLetter(tag)}</p>`;
  });

  blogHTML = blogHTML.replace('"BLOG TAGS"', tagDiv.outerHTML);

  document.querySelector(".main-section").innerHTML += blogHTML;
}

window.addEventListener("scroll", load_more);
