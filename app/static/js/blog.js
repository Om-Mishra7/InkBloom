function viewStats() {
  if (localStorage.getItem(window.location.pathname.replace("/blogs/", ""))) {
    const lastView = localStorage.getItem(window.location.pathname.replace("/blogs/", ""));
    if (new Date().getTime() - lastView < 60000) {
      setTimeout(() => {
        viewStats();
      }
        , 60000);
      return;
    }
  }
  localStorage.setItem(window.location.pathname.replace("/blogs/", ""), new Date().getTime());
  fetch(`/api/v1/statisics/views/${window.location.pathname.replace("/blogs/", "")}`, {
    method: "POST",
  })
    .then((response) => {
      if (response.status === 200) {
        return response.json();
      } else {
        throw new Error("Error");
      }
    })
    .catch((error) => {
      console.log(error);
      setTimeout(() => {
        viewStats();
      }
        , 60000);
    });
}

let commentForm = document.getElementById("comment-form");

commentForm.addEventListener("submit", (e) => {
  e.preventDefault();
  let comment = document.getElementById("comment").value;
  let name = document.getElementById("name").value;
  let email = document.getElementById("email").value;
  let blogId = document.getElementById("blog-id").value;
  let commentData = {
    comment: comment,
    name: name,
    email: email,
    blogId: blogId,
  };
  fetch("/api/v1/user/comments", {
    method: "POST",
    body: JSON.stringify(commentData),
    headers: {
      "Content-Type": "application/json",
    },
  })
    .then((response) => {
      if (response.status === 200) {
        return response.json();
      } else {
        throw new Error("Error");
      }
    })
    .then((data) => {
      window.location.reload();
    })
    .catch((error) => {
      console.log(error);
    });
}
);

hljs.highlightAll(); // Ensure that the code blocks are still syntax highlighted

viewStats();

